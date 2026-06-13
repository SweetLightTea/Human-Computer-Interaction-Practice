using UnityEngine;

/// <summary>
/// 挂在敌人子物体 HintTrigger 上，将触发事件转发给父级 Enemy
/// </summary>
public class EnemyHintTrigger : MonoBehaviour
{
    public Enemy enemy;

    private void OnTriggerEnter2D(Collider2D collision)
    {
        if (collision.gameObject.CompareTag("Player") && enemy != null)
        {
            enemy.OnPlayerEnterHintRange();
        }
    }

    private void OnTriggerExit2D(Collider2D collision)
    {
        if (collision.gameObject.CompareTag("Player") && enemy != null)
        {
            enemy.OnPlayerExitHintRange();
        }
    }
}
