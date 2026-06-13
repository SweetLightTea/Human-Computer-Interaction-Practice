using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class PlayerState
{
    protected PlayerStateMachine stateMachine;
    protected Player player;

    protected Rigidbody2D rb;

    protected float xInput;
    protected float yInput;

    private string animBoolName;

    protected float stateTimer;
    protected bool triggerCalled;

    public PlayerState(Player _player, PlayerStateMachine _stateMachine, string _animBoolName)
    {
        this.player = _player;
        this.stateMachine = _stateMachine;
        this.animBoolName = _animBoolName;
    }

    public virtual void Enter()
    {
        player.anim.SetBool(animBoolName, true);
        rb = player.rb;
        triggerCalled = false;
    }

    public virtual void Update()
    {
        stateTimer -= Time.deltaTime;

        // 手势输入优先，键盘输入作为后备
        if (GestureReceiver.IsActive && GestureReceiver.MoveAxis != 0f)
            xInput = GestureReceiver.MoveAxis;
        else
            xInput = Input.GetAxisRaw("Horizontal");

        yInput = Input.GetAxisRaw("Vertical");

        // 装弹在所有状态下都可用（手势 + 键盘）
        if (GestureReceiver.ReloadTriggered || Input.GetKeyDown(KeyCode.Q))
            player.Reload();
    }

    public virtual void Exit()
    {
        player.anim.SetBool(animBoolName, false);
    }

    public virtual void AnimationFinishTrigger()
    {
        triggerCalled = true;
    }
}