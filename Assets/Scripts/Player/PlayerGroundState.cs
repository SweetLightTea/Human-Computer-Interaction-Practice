using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class PlayerGroundState : PlayerState
{
    public PlayerGroundState(Player _player, PlayerStateMachine _stateMachine, string _animBoolName) : base(_player, _stateMachine, _animBoolName)
    {
    }

    public override void Enter()
    {
        base.Enter();
    }

    public override void Exit()
    {
        base.Exit();
    }

    public override void Update()
    {
        base.Update();

        // 开枪：手势握拳 或 鼠标左键
        if (GestureReceiver.FireTriggered || Input.GetMouseButtonDown(0))
        {
            if (player.CanShoot())
                player.Shot();
        }

        if (!player.IsGroundDetected())
            stateMachine.ChangeState(player.fallState);

        // 跳跃：手势四指朝上 或 空格键
        if ((GestureReceiver.JumpTriggered || Input.GetKeyDown(KeyCode.Space))
            && player.IsGroundDetected())
            stateMachine.ChangeState(player.jumpState);
    }
}
