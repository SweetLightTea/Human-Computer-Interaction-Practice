using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class EnemyHp_UI : MonoBehaviour
{
    private Enemy enemy;
    private RectTransform myTransform;
    private Slider slider;

    private void Start()
    {
        myTransform = GetComponent<RectTransform>();
        enemy = GetComponentInParent<Enemy>();
        slider = GetComponentInChildren<Slider>();

        enemy.onFlipped += FlipUI;
        enemy.onHpChanged += UpdateHpUI;
    }

    private void UpdateHpUI()
    {
        slider.maxValue = enemy.maxHp;
        slider.value = enemy.currentHp;
    }

    private void FlipUI()
    {
        myTransform.Rotate(0, 180, 0);
    }
}
