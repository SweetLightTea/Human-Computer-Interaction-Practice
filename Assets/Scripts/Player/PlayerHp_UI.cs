using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class PlayerHp_UI : MonoBehaviour
{
    private Player player;
    private RectTransform myTransform;
    private Slider slider;

    private void Start()
    {
        myTransform = GetComponent<RectTransform>();
        player = GetComponentInParent<Player>();
        slider = GetComponentInChildren<Slider>();

        player.onFlipped += FlipUI;
        player.onHpChanged += UpdateHpUI;
    }

    private void UpdateHpUI()
    {
        slider.maxValue = player.maxHp;
        slider.value = player.currentHp;
    }

    private void FlipUI()
    {
        myTransform.Rotate(0, 180, 0);
    }
}
