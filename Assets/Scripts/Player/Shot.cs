using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Shot : MonoBehaviour
{
    private Rigidbody2D rb;
    private CircleCollider2D cc;

    public int facingDir;
    public int attack = 10;

    public float speed;
    private float life;

    private void Start()
    {
        rb = GetComponent<Rigidbody2D>();
        cc = GetComponent<CircleCollider2D>();

        life = 5;
        rb.velocity = new Vector2(speed * facingDir, 0);
    }

    private void Update()
    {
        life -= Time.deltaTime;

        if (life < 0)
            Destroy(this.gameObject);
    }

    private void OnTriggerEnter2D(Collider2D collision)
    {
        if (collision.gameObject.CompareTag("Enemy"))
        {
            collision.GetComponent<Enemy>().TakeDamage(attack);
        }
    }
}
