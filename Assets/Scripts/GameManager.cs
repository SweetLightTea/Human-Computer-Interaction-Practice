using UnityEngine;
using UnityEngine.SceneManagement;

public class GameManager : MonoBehaviour
{
    public static GameManager instance { get; private set; }

    // 重新开始游戏时跳过主菜单，直接进入游戏
    private static bool skipMenuOnLoad = false;

    [Header("界面面板（可选：不拖入则直接开始游戏）")]
    [SerializeField] private GameObject mainMenuPanel;
    [SerializeField] private GameObject gameOverPanel;
    [SerializeField] private GameObject hudPanel;

    private bool gameOverTriggered;
    private bool hasMainMenu;

    private void Awake()
    {
        if (instance == null)
            instance = this;
        else
            Destroy(gameObject);
    }

    private void Start()
    {
        hasMainMenu = (mainMenuPanel != null);

        // 如果是从"重新开始"过来的，直接进入游戏
        if (skipMenuOnLoad)
        {
            skipMenuOnLoad = false;
            if (hasMainMenu)
            {
                StartGame();
                return;
            }
        }

        if (hasMainMenu)
        {
            ShowMainMenu();
        }
        else
        {
            Time.timeScale = 1f;
            gameOverTriggered = false;
        }
    }

    #region 游戏流程控制

    public void StartGame()
    {
        if (mainMenuPanel != null)
            mainMenuPanel.SetActive(false);
        if (gameOverPanel != null)
            gameOverPanel.SetActive(false);
        if (hudPanel != null)
            hudPanel.SetActive(true);

        Time.timeScale = 1f;
        gameOverTriggered = false;

        // 监听玩家死亡事件
        Player player = FindObjectOfType<Player>();
        if (player != null)
            player.onDeath += OnPlayerDeath;

        // 显示移动操作提示
        TutorialUI.instance?.ShowMovementHint();
    }

    public void GameOver()
    {
        if (gameOverTriggered) return;
        gameOverTriggered = true;

        if (hudPanel != null)
            hudPanel.SetActive(false);
        if (gameOverPanel != null)
            gameOverPanel.SetActive(true);

        Time.timeScale = 0f;
    }

    /// <summary>
    /// 重新开始：重新加载场景，直接进入游戏（跳过主菜单）
    /// </summary>
    public void RestartGame()
    {
        skipMenuOnLoad = true;
        Time.timeScale = 1f;
        SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
    }

    /// <summary>
    /// 返回主菜单：重新加载场景，显示开始界面
    /// </summary>
    public void ReturnToMainMenu()
    {
        skipMenuOnLoad = false;
        Time.timeScale = 1f;
        SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
    }

    /// <summary>
    /// 退出游戏程序
    /// </summary>
    public void ExitGame()
    {
#if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
#else
        Application.Quit();
#endif
    }

    private void ShowMainMenu()
    {
        if (mainMenuPanel != null)
            mainMenuPanel.SetActive(true);
        if (gameOverPanel != null)
            gameOverPanel.SetActive(false);
        if (hudPanel != null)
            hudPanel.SetActive(false);

        Time.timeScale = 0f;
    }

    private void OnPlayerDeath()
    {
        StartCoroutine(DelayedGameOver());
    }

    private System.Collections.IEnumerator DelayedGameOver()
    {
        yield return new WaitForSeconds(2f);
        GameOver();
    }

    #endregion
}
