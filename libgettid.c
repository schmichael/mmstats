#include <sys/syscall.h>
#include <unistd.h>

int gettid(void);

int gettid()
{ 
    return syscall(SYS_gettid);
}
