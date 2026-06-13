using UnityEngine;

public class CameraController : MonoBehaviour
{
    [SerializeField] private Transform player;
    [SerializeField] private float smoothSpeed = 5f;
    [SerializeField] private Vector3 offset = new Vector3(0, 2, -10);

    private void Start()
    {
        if (player == null)
        {
            player = GameObject.FindGameObjectWithTag("Player").transform;
        }
    }

    private void LateUpdate()
    {
        if (player == null) return;

        // 跟随玩家位置，不会因为玩家翻转而翻转
        Vector3 targetPosition = new Vector3(
            player.position.x + offset.x,
            player.position.y + offset.y,
            offset.z
        );

        transform.position = Vector3.Lerp(transform.position, targetPosition, smoothSpeed * Time.deltaTime);
    }
}
