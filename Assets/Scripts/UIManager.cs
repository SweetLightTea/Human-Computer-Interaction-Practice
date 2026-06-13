using UnityEngine;
using UnityEngine.UI;

public class UIManager : MonoBehaviour
{
    [Header("UI 引用")]
    [SerializeField] private Text ammoText;
    [SerializeField] private Text gemText;
    [SerializeField] private Text reloadHintText;

    [Header("玩家引用")]
    [SerializeField] private Player player;

    private void Start()
    {
        if (player == null)
        {
            player = GameObject.FindGameObjectWithTag("Player").GetComponent<Player>();
        }

        // 订阅事件
        player.onAmmoChanged += UpdateAmmoUI;
        player.onGemChanged += UpdateGemUI;

        // 初始刷新
        UpdateAmmoUI();
        UpdateGemUI();

        if (reloadHintText != null)
            reloadHintText.gameObject.SetActive(false);
    }

    private void Update()
    {
        // 当弹药为0时显示换弹提示
        if (reloadHintText != null)
        {
            bool shouldShow = player.currentAmmo <= 0 && !player.isDead;
            if (reloadHintText.gameObject.activeSelf != shouldShow)
                reloadHintText.gameObject.SetActive(shouldShow);
        }
    }

    private void UpdateAmmoUI()
    {
        if (ammoText != null)
        {
            ammoText.text = "弹药: " + player.currentAmmo + " / " + player.maxAmmo;

            // 弹药不足时变红
            if (player.currentAmmo <= 5)
                ammoText.color = Color.red;
            else
                ammoText.color = Color.white;
        }
    }

    private void UpdateGemUI()
    {
        if (gemText != null)
        {
            gemText.text = "宝石: " + player.gemCount;
        }
    }

    private void OnDestroy()
    {
        if (player != null)
        {
            player.onAmmoChanged -= UpdateAmmoUI;
            player.onGemChanged -= UpdateGemUI;
        }
    }
}
