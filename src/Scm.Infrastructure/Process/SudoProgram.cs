namespace Scm.Infrastructure.Process;

/// <summary>Білий список програм, які сервіс запускає через sudo (збігається з <c>pi/sudoers.d/scm</c>).</summary>
public enum SudoProgram
{
    ScmUser,
    ScmStatus,
    ScmLogs,
    Snap,
    Backup,
    ScmUpdate,
}
