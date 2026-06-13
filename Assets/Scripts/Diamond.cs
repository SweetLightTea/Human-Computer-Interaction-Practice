using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Diamond : MonoBehaviour
{
    private Rigidbody2D rb;
    private bool playerInRange;

    private void Start()
    {
        rb = GetComponent<Rigidbody2D>();
        rb.velocity = new Vector2(Random.Range(-5, 5), Random.Range(8, 12));
    }

    private void Update()
    {
        if (playerInRange && (GestureReceiver.InteractTriggered || Input.GetMouseButtonDown(1)))
        {
            // 通知玩家收集宝石
            Player player = GameObject.FindGameObjectWithTag("Player").GetComponent<Player>();
            if (player != null)
            {
                player.CollectGem(1);
            }
            Destroy(this.gameObject);
        }
    }

    private void OnTriggerEnter2D(Collider2D collision)
    {
        if (collision.gameObject.CompareTag("Player"))
        {
            //Debug.Log("PlayerInRange");
            playerInRange = true;
        }
    }
}