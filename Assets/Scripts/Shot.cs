using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Shot : MonoBehaviour
{
    public Player player;
    private Rigidbody2D rb;

    public float speed;
    private float life;

    private void Start()
    {
        player = FindObjectOfType<Player>();
        rb = GetComponent<Rigidbody2D>();

        life = 5;
        rb.velocity = new Vector2(speed * player.facingDir, 0);
    }

    private void Update()
    {
        life -= Time.deltaTime;

        if (life < 0)
            Destroy(this.gameObject);
    }
}
