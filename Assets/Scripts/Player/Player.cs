using System;
using Unity.VisualScripting;
using UnityEngine;

public class Player : MonoBehaviour
{
    public float moveSpeed;
    public float jumpForce;
    
    public Animator anim { get; private set; }
    public Rigidbody2D rb { get; private set; }
    public CapsuleCollider2D cd { get; private set; }

    public int facingDir { get; private set; } = 1;
    private bool facingRight = true;

    public System.Action onFlipped;
    public System.Action onHpChanged;
    public System.Action onAmmoChanged;
    public System.Action onGemChanged;
    public System.Action onDeath;

    public Transform shotPosition;
    public GameObject shotPrefab;

    public int maxHp = 100;
    public int currentHp;
    public bool isDead;

    // 弹药系统
    public int maxAmmo = 20;
    public int currentAmmo;
    public bool isReloading;

    // 宝石系统
    public int gemCount;

    [SerializeField] protected Transform groundCheck;
    [SerializeField] protected float groundCheckDistance;
    [SerializeField] protected LayerMask whatIsGround;

    public PlayerStateMachine stateMachine { get; private set; }
    public PlayerIdleState idleState { get; private set; }
    public PlayerMoveState moveState { get; private set; }
    public PlayerJumpState jumpState { get; private set; }
    public PlayerDoubleJumpState doubleJumpState { get; private set; }
    public PlayerFallState fallState { get; private set; }
    public PlayerDeadState deadState { get; private set; }


    private void Awake()
    {
        stateMachine = new PlayerStateMachine();

        idleState = new PlayerIdleState(this, stateMachine, "Idle");
        moveState = new PlayerMoveState(this, stateMachine, "Move");
        jumpState = new PlayerJumpState(this, stateMachine, "Jump");
        doubleJumpState = new PlayerDoubleJumpState(this, stateMachine, "DoubleJump");
        fallState = new PlayerFallState(this, stateMachine, "Jump");
        deadState = new PlayerDeadState(this, stateMachine, "Dead");
    }

    private void Start()
    {
        anim = GetComponentInChildren<Animator>();
        rb = GetComponent<Rigidbody2D>();
        cd = GetComponent<CapsuleCollider2D>();

        stateMachine.Initialize(idleState);

        currentHp = maxHp;
        currentAmmo = maxAmmo;
        gemCount = 0;

        if (onHpChanged != null)
            onHpChanged();
        if (onAmmoChanged != null)
            onAmmoChanged();
        if (onGemChanged != null)
            onGemChanged();
    }

    private void Update()
    {
        stateMachine.currentState.Update();
    }

    public bool CanShoot()
    {
        return currentAmmo > 0 && !isReloading;
    }

    public void Shot()
    {
        if (!CanShoot()) return;

        currentAmmo--;
        GameObject shot = Instantiate(shotPrefab, shotPosition.position, Quaternion.identity);
        shot.GetComponent<Shot>().facingDir = this.facingDir;

        if (onAmmoChanged != null)
            onAmmoChanged();
    }

    public void Reload()
    {
        if (isReloading) return;
        if (currentAmmo >= maxAmmo) return;

        isReloading = true;
        // 可以在这里添加换弹动画
        currentAmmo = maxAmmo;
        isReloading = false;

        if (onAmmoChanged != null)
            onAmmoChanged();
    }

    public void CollectGem(int amount = 1)
    {
        gemCount += amount;
        if (onGemChanged != null)
            onGemChanged();
    }

    public void TakeDamage(int _damage)
    {
        if (currentHp - _damage > 0)
        {
            currentHp -= _damage;
        }
        else
        {
            currentHp = 0;
            isDead = true;
            stateMachine.ChangeState(deadState);

            if (onDeath != null)
                onDeath();
        }

        onHpChanged();
    }

    #region velocity
    public void SetVelocity(float _xVelocity, float _yVelocity)
    {
        rb.velocity = new Vector2(_xVelocity, _yVelocity);
        FlipController(_xVelocity);
    }

    public void SetZeroVelocity()
    {
        rb.velocity = new Vector2 (0, 0);
    }
    #endregion

    public virtual bool IsGroundDetected() => Physics2D.Raycast(groundCheck.position, Vector2.down, groundCheckDistance, whatIsGround);

    #region Flip
    public virtual void Flip()
    {
        facingDir *= -1;
        facingRight = !facingRight;
        transform.Rotate(0, 180, 0);

        if (onFlipped != null)
            onFlipped();
    }

    public virtual void FlipController(float _x)
    {
        if (_x > 0 && !facingRight)
            Flip();
        else if (_x < 0 && facingRight)
            Flip();
    }

    public virtual void SetupDefaultFacingDir(int _direction)
    {
        facingDir = _direction;

        if (facingDir == -1)
            facingRight = false;
    }
    #endregion

    protected virtual void OnDrawGizmos()
    {
        Gizmos.DrawLine(groundCheck.position, new Vector3(groundCheck.position.x, groundCheck.position.y - groundCheckDistance));
        //Gizmos.DrawLine(shotPosition.position, new Vector3(shotPosition.position.x + .05f, shotPosition.position.y));
    }
}