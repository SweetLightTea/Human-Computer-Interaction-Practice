using UnityEngine;
using UnityEngine.UI;

public class GameOverUI : MonoBehaviour
{
    [Header("按钮（留空则自动查找子物体中的 Button）")]
    [SerializeField] private Button restartButton;
    [SerializeField] private Button exitButton;

    private void Awake()
    {
        // 如果没拖入按钮，自动查找
        if (restartButton == null || exitButton == null)
        {
            Button[] buttons = GetComponentsInChildren<Button>(true);
            foreach (Button btn in buttons)
            {
                if (btn.name.Contains("Restart") || btn.name.Contains("重新"))
                    restartButton = btn;
                else if (btn.name.Contains("Exit") || btn.name.Contains("退出"))
                    exitButton = btn;
            }
        }
    }

    private void OnEnable()
    {
        if (restartButton != null)
        {
            restartButton.onClick.RemoveAllListeners();
            restartButton.onClick.AddListener(OnRestartGame);
        }
        else
            Debug.LogWarning("GameOverUI: restartButton 未找到");

        if (exitButton != null)
        {
            exitButton.onClick.RemoveAllListeners();
            exitButton.onClick.AddListener(OnReturnToMenu);
        }
        else
            Debug.LogWarning("GameOverUI: exitButton 未找到");
    }

    private void OnRestartGame()
    {
        Debug.Log("点击了重新开始按钮 → 直接进入游戏");
        if (GameManager.instance != null)
            GameManager.instance.RestartGame();
        else
            Debug.LogError("GameManager.instance 为空！");
    }

    private void OnReturnToMenu()
    {
        Debug.Log("点击了退出游戏按钮 → 返回开始界面");
        if (GameManager.instance != null)
            GameManager.instance.ReturnToMainMenu();
        else
            Debug.LogError("GameManager.instance 为空！");
    }
}
