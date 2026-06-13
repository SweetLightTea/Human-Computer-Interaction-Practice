using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

/// <summary>
/// 手势接收器 — 通过 UDP 接收 Python 端发送的手势数据，
/// 将手势状态暴露为静态属性，供 Player/Chest/Diamond 等脚本直接读取。
///
/// 数据流: Python(MediaPipe) → UDP → GestureReceiver → 静态属性 → Player/Chest/Diamond
///
/// 不依赖操作系统按键模拟，不受窗口焦点影响。
/// </summary>
public class GestureReceiver : MonoBehaviour
{
    [Header("UDP 设置")]
    [SerializeField] private int listenPort = 12345;

    [Header("调试")]
    [SerializeField] private bool logGestures = false;

    // ================================================================
    //  静态属性（游戏脚本通过以下属性读取手势）
    // ================================================================

    /// <summary>水平移动轴: -1(左) / 0(停) / 1(右)</summary>
    public static float MoveAxis { get; private set; }

    /// <summary>跳跃触发（当帧为 true，下一帧自动复位）</summary>
    public static bool JumpTriggered { get; private set; }

    /// <summary>开火触发（握拳时周期性为 true）</summary>
    public static bool FireTriggered { get; private set; }

    /// <summary>交互触发（五指张开时周期性为 true）</summary>
    public static bool InteractTriggered { get; private set; }

    /// <summary>装弹触发（拇指朝上时为 true）</summary>
    public static bool ReloadTriggered { get; private set; }

    /// <summary>是否有手势数据接入</summary>
    public static bool IsActive { get; private set; }

    // ================================================================
    //  内部状态
    // ================================================================

    private UdpClient _udpClient;
    private Thread _receiveThread;
    private volatile bool _running;

    // UDP 线程写入，主线程读取
    private string _moveDirection = "NONE";
    private bool _jump;
    private string _rightGesture = "NONE";
    private readonly object _lock = new object();

    // 冷却计时
    private float _lastFireTime, _lastInteractTime, _lastReloadTime;
    private const float FireCooldown = 0.25f;
    private const float InteractCooldown = 0.5f;
    private const float ReloadCooldown = 1.0f;

    // 数据超时：超过此时间没收到的数据则认为手势失联
    private int _lastDataTick;  // 使用 Environment.TickCount（线程安全）
    private const int DataTimeoutMs = 500;

    private void Start()
    {
        StartUDPListener();
    }

    private void Update()
    {
        // 从 UDP 线程安全地读取最新手势数据
        string moveDir;
        bool jump;
        string rightGes;
        lock (_lock)
        {
            moveDir = _moveDirection;
            jump = _jump;
            rightGes = _rightGesture;
            _jump = false; // 跳跃是单次触发，读取后清除
        }

        // 检查数据是否超时（使用 TickCount 因为 UDP 线程不能访问 Time）
        if (Environment.TickCount - _lastDataTick > DataTimeoutMs)
        {
            MoveAxis = 0f;
            IsActive = false;
            return;
        }

        IsActive = true;

        // === 左手：移动（连续值）===
        if (moveDir == "LEFT")
            MoveAxis = -1f;
        else if (moveDir == "RIGHT")
            MoveAxis = 1f;
        else
            MoveAxis = 0f;

        // === 左手：跳跃（单次触发）===
        JumpTriggered = jump;

        // === 右手：战斗/交互（带冷却的单次触发）===
        float now = Time.unscaledTime;

        if (rightGes == "FIST" && now - _lastFireTime >= FireCooldown)
        {
            FireTriggered = true;
            _lastFireTime = now;
        }
        else
        {
            FireTriggered = false;
        }

        if (rightGes == "OPEN_PALM" && now - _lastInteractTime >= InteractCooldown)
        {
            InteractTriggered = true;
            _lastInteractTime = now;
        }
        else
        {
            InteractTriggered = false;
        }

        if (rightGes == "THUMB_UP" && now - _lastReloadTime >= ReloadCooldown)
        {
            ReloadTriggered = true;
            _lastReloadTime = now;
        }
        else
        {
            ReloadTriggered = false;
        }

        if (logGestures)
        {
            string log = $"[Gesture] Move:{MoveAxis} Jump:{JumpTriggered} Fire:{FireTriggered} Interact:{InteractTriggered} Reload:{ReloadTriggered}";
            if (_prevLog != log)
            {
                Debug.Log(log);
                _prevLog = log;
            }
        }
    }

    private string _prevLog;

    private void LateUpdate()
    {
        // 一帧结束后复位单次触发标志
        // （其他脚本的 Update 已在之前读取完毕）
        JumpTriggered = false;
        FireTriggered = false;
        InteractTriggered = false;
        ReloadTriggered = false;
    }

    private void OnDestroy()
    {
        _running = false;
        _receiveThread?.Join(500);
        _udpClient?.Close();
    }

    #region UDP

    private void StartUDPListener()
    {
        _running = true;
        _receiveThread = new Thread(ReceiveLoop)
        {
            IsBackground = true,
            Name = "GestureUDPListener"
        };
        _receiveThread.Start();
        Debug.Log($"[GestureReceiver] UDP 监听已启动，端口: {listenPort}");
    }

    private void ReceiveLoop()
    {
        try
        {
            _udpClient = new UdpClient(listenPort);
            IPEndPoint remoteEP = new IPEndPoint(IPAddress.Any, listenPort);

            while (_running)
            {
                byte[] data = _udpClient.Receive(ref remoteEP);
                string json = Encoding.UTF8.GetString(data);
                ParseGesture(json);
            }
        }
        catch (SocketException ex)
        {
            if (_running)
                Debug.LogError($"[GestureReceiver] UDP 错误: {ex.Message}");
        }
        catch (Exception ex)
        {
            if (_running)
                Debug.LogError($"[GestureReceiver] 错误: {ex.Message}");
        }
    }

    private void ParseGesture(string json)
    {
        try
        {
            var gesture = JsonUtility.FromJson<GestureData>(json);

            lock (_lock)
            {
                _moveDirection = gesture.left_hand.move_direction;
                // 跳跃只在检测到时累积（Python 端已做冷却）
                if (gesture.left_hand.jump)
                    _jump = true;
                _rightGesture = gesture.right_hand.gesture;
            }

            _lastDataTick = Environment.TickCount;
        }
        catch (Exception ex)
        {
            Debug.LogError($"[GestureReceiver] JSON 解析错误: {ex.Message}\n{json}");
        }
    }

    #endregion

    #region JSON 数据结构

    [Serializable]
    private class GestureData
    {
        public LeftHandData left_hand;
        public RightHandData right_hand;
    }

    [Serializable]
    private class LeftHandData
    {
        public bool detected;
        public string move_direction;
        public bool jump;
    }

    [Serializable]
    private class RightHandData
    {
        public bool detected;
        public string gesture;
    }

    #endregion
}
