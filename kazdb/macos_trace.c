#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <signal.h>
#include <mach/mach.h>
#include <mach/task.h>
#include <mach/thread_act.h>
#include <sys/wait.h>

void child_process() {
    printf("Child process (PID: %d) starting\n", getpid());
    
    while(1) {
        printf("Child running...\n");
        sleep(1);
        sleep(1);
        sleep(1);
        // kill(getpid(), SIGSTOP);

        // exec into the "test" program in the current directory
        char *args[] = { "./test", NULL };
        execvp(args[0], args);
    }
}

void inspect_task(pid_t child_pid) {
    mach_port_t task;
    kern_return_t kr;
    
    // Get the task port for the child process
    kr = task_for_pid(mach_task_self(), child_pid, &task);
    if (kr != KERN_SUCCESS) {
        printf("Failed to get task for pid: %s\n", mach_error_string(kr));
        return;
    }

    // Get thread list
    thread_act_array_t thread_list;
    mach_msg_type_number_t thread_count;
    kr = task_threads(task, &thread_list, &thread_count);
    if (kr != KERN_SUCCESS) {
        printf("Failed to get threads: %d\n", kr);
        return;
    }

    printf("Process has %d threads\n", thread_count);

    // Inspect each thread
    for (int i = 0; i < thread_count; i++) {
        thread_t thread = thread_list[i];
        
        // Get thread state
        arm_thread_state64_t thread_state;
        mach_msg_type_number_t state_count = ARM_THREAD_STATE64_COUNT;
        kr = thread_get_state(thread, ARM_THREAD_STATE64, 
                            (thread_state_t)&thread_state, 
                            &state_count);
        
        if (kr == KERN_SUCCESS) {
            printf("Thread %d PC: 0x%llx\n", i, thread_state.__pc);
            printf("Thread %d SP: 0x%llx\n", i, thread_state.__sp);
            printf("Thread %d x17: 0x%llx\n", i, thread_state.__x[17]);
            printf("Thread %d x18: 0x%llx\n", i, thread_state.__x[18]);
            // Can print other registers here too
        }
        
        // Clean up thread reference
        mach_port_deallocate(mach_task_self(), thread);
    }

    // Clean up thread list
    vm_deallocate(mach_task_self(), (vm_address_t)thread_list, 
                 thread_count * sizeof(thread_act_t));
    
    // Clean up task port
    mach_port_deallocate(mach_task_self(), task);
}

void parent_process(pid_t child_pid) {
    int status;
    printf("Parent process (PID: %d) monitoring child (PID: %d)\n", 
           getpid(), child_pid);

    while(1) {
        waitpid(child_pid, &status, WUNTRACED | WCONTINUED);
        
        if (WIFSTOPPED(status)) {
            printf("Child was stopped by signal %d\n", WSTOPSIG(status));
            
            // Inspect the process
            inspect_task(child_pid);
            
            printf("Sending SIGCONT to child...\n");
            kill(child_pid, SIGCONT);
        }
        else if (WIFCONTINUED(status)) {
            printf("Child was continued\n");
        }
        else if (WIFEXITED(status)) {
            printf("Child exited normally with status 0x%llx\n", WEXITSTATUS(status));
            break;
        }
        else if (WIFSIGNALED(status)) {
            printf("Child was terminated by signal\n");
            break;
        }
    }
}

int main() {
    pid_t pid = fork();
    
    if (pid < 0) {
        perror("Fork failed");
        exit(1);
    }
    else if (pid == 0) {
        child_process();
    }
    else {
        parent_process(pid);
    }
    
    return 0;
}