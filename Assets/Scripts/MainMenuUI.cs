using UnityEngine;
using UnityEngine.UI;

public class MainMenuUI : MonoBehaviour
{
    [Header("按钮（留空则自动查找子物体中的 Button）")]
    [SerializeField] private Button startButton;
    [SerializeField] private Button exitButton;
    [SerializeField] private Button instructionsButton;

    [Header("游戏说明面板")]
    [SerializeField] private GameObject instructionsPanel;
    [SerializeField] private Button closeInstructionsButton;

    private void Awake()
    {
        // 如果没拖入按钮，自动查找
        Button[] buttons = GetComponentsInChildren<Button>(true);
        foreach (Button btn in buttons)
        {
            if (btn.name.Contains("Start") || btn.name.Contains("开始"))
                startButton = btn;
            else if (btn.name.Contains("Exit") || btn.name.Contains("退出"))
                exitButton = btn;
            else if (btn.name.Contains("Instructions") || btn.name.Contains("说明"))
                instructionsButton = btn;
            else if (btn.name.Contains("Close") || btn.name.Contains("关闭"))
                closeInstructionsButton = btn;
        }
    }

    private void OnEnable()
    {
        // 每次面板激活时重新绑定
        if (startButton != null)
        {
            startButton.onClick.RemoveAllListeners();
            startButton.onClick.AddListener(OnStartGame);
        }
        else
            Debug.LogWarning("MainMenuUI: startButton 未找到");

        if (exitButton != null)
        {
            exitButton.onClick.RemoveAllListeners();
            exitButton.onClick.AddListener(OnExitGame);
        }
        else
            Debug.LogWarning("MainMenuUI: exitButton 未找到");

        if (instructionsButton != null)
        {
            instructionsButton.onClick.RemoveAllListeners();
            instructionsButton.onClick.AddListener(OnShowInstructions);
        }
        else
            Debug.LogWarning("MainMenuUI: instructionsButton 未找到");

        if (closeInstructionsButton != null)
        {
            closeInstructionsButton.onClick.RemoveAllListeners();
            closeInstructionsButton.onClick.AddListener(OnCloseInstructions);
        }
        else
            Debug.LogWarning("MainMenuUI: closeInstructionsButton 未找到");

        // 初始隐藏说明面板
        if (instructionsPanel != null)
            instructionsPanel.SetActive(false);
    }

    private void OnStartGame()
    {
        Debug.Log("点击了开始游戏按钮");
        if (GameManager.instance != null)
            GameManager.instance.StartGame();
        else
            Debug.LogError("GameManager.instance 为空！");
    }

    private void OnExitGame()
    {
        Debug.Log("点击了退出游戏按钮");
        if (GameManager.instance != null)
            GameManager.instance.ExitGame();
        else
            Debug.LogError("GameManager.instance 为空！");
    }

    private void OnShowInstructions()
    {
        if (instructionsPanel != null)
            instructionsPanel.SetActive(true);
    }

    private void OnCloseInstructions()
    {
        if (instructionsPanel != null)
            instructionsPanel.SetActive(false);
    }
}
