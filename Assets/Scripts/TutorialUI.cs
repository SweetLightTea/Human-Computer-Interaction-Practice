using UnityEngine;
using UnityEngine.UI;
using System.Collections;

public class TutorialUI : MonoBehaviour
{
    public static TutorialUI instance { get; private set; }

    [Header("UI 组件")]
    [SerializeField] private GameObject hintPanel;
    [SerializeField] private Text hintText;
    [SerializeField] private float movementHintDuration = 8f;

    [Header("提示文字内容")]
    [SerializeField] private string movementHint = "[A/D] 移动  [空格] 跳跃（可二段跳）";
    [SerializeField] private string chestHint = "[鼠标右键] 打开宝箱，再按右键捡取钻石";
    [SerializeField] private string enemyHint = "[鼠标左键] 开火射击敌人  [Q] 装弹";

    // 当前活跃的提示类型（优先级：敌人 > 宝箱 > 移动）
    private enum HintType { None, Movement, Chest, Enemy }
    private HintType currentHint = HintType.None;

    private int chestInRangeCount = 0;
    private int enemyInRangeCount = 0;
    private Coroutine movementHintCoroutine;

    private void Awake()
    {
        if (instance == null)
            instance = this;
        else
            Destroy(gameObject);
    }

    private void Start()
    {
        if (hintPanel != null)
            hintPanel.SetActive(false);
    }

    /// <summary>
    /// 游戏开始时调用：显示移动跳跃提示（持续一段时间后自动消失）
    /// </summary>
    public void ShowMovementHint()
    {
        if (movementHintCoroutine != null)
            StopCoroutine(movementHintCoroutine);

        currentHint = HintType.Movement;
        movementHintCoroutine = StartCoroutine(MovementHintRoutine());
    }

    private IEnumerator MovementHintRoutine()
    {
        ShowHint(movementHint);
        yield return new WaitForSeconds(movementHintDuration);
        // 时间到后，如果当前仍然是移动提示，则隐藏
        if (currentHint == HintType.Movement)
        {
            HideHint();
            currentHint = HintType.None;
        }
        movementHintCoroutine = null;
    }

    /// <summary>
    /// 玩家进入宝箱范围：显示宝箱提示
    /// </summary>
    public void OnEnterChestRange()
    {
        chestInRangeCount++;
        RefreshHint();
    }

    /// <summary>
    /// 玩家离开宝箱范围
    /// </summary>
    public void OnExitChestRange()
    {
        chestInRangeCount--;
        if (chestInRangeCount < 0) chestInRangeCount = 0;
        RefreshHint();
    }

    /// <summary>
    /// 玩家进入敌人范围：显示战斗提示
    /// </summary>
    public void OnEnterEnemyRange()
    {
        enemyInRangeCount++;
        RefreshHint();
    }

    /// <summary>
    /// 玩家离开敌人范围
    /// </summary>
    public void OnExitEnemyRange()
    {
        enemyInRangeCount--;
        if (enemyInRangeCount < 0) enemyInRangeCount = 0;
        RefreshHint();
    }

    /// <summary>
    /// 根据优先级刷新提示
    /// 优先级：敌人 > 宝箱 > 移动 > 无
    /// </summary>
    private void RefreshHint()
    {
        if (enemyInRangeCount > 0)
        {
            currentHint = HintType.Enemy;
            ShowHint(enemyHint);
            // 停止移动提示的协程
            if (movementHintCoroutine != null)
            {
                StopCoroutine(movementHintCoroutine);
                movementHintCoroutine = null;
            }
        }
        else if (chestInRangeCount > 0)
        {
            currentHint = HintType.Chest;
            ShowHint(chestHint);
        }
        else if (currentHint == HintType.Enemy || currentHint == HintType.Chest)
        {
            // 敌人和宝箱都不在范围了，检查是否还有移动提示在跑
            if (movementHintCoroutine != null)
            {
                currentHint = HintType.Movement;
                ShowHint(movementHint);
            }
            else
            {
                HideHint();
                currentHint = HintType.None;
            }
        }
    }

    private void ShowHint(string message)
    {
        if (hintPanel != null)
            hintPanel.SetActive(true);
        if (hintText != null)
            hintText.text = message;
    }

    private void HideHint()
    {
        if (hintPanel != null)
            hintPanel.SetActive(false);
    }
}
