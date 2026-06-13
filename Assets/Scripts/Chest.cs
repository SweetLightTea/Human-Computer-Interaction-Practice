using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class Chest : MonoBehaviour
{
    private Animator anim;
    private bool playerInRange;

    [SerializeField] private GameObject diamond;

    private void Start()
    {
        anim = GetComponent<Animator>();
    }

    private void Update()
    {
        if (playerInRange && (GestureReceiver.InteractTriggered || Input.GetMouseButtonDown(1)))
            anim.SetBool("Open", true);
    }

    public void Open()
    {
        Instantiate(diamond, transform.position, Quaternion.identity);
    }

    private void OnTriggerEnter2D(Collider2D collision)
    {
        if (collision.gameObject.CompareTag("Player"))
        {
            playerInRange = true;
            TutorialUI.instance?.OnEnterChestRange();
        }
    }

    private void OnTriggerExit2D(Collider2D collision)
    {
        if (collision.gameObject.CompareTag("Player"))
        {
            playerInRange = false;
            TutorialUI.instance?.OnExitChestRange();
        }
    }
}
