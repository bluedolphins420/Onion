#ifndef PROCESS_H__
#define PROCESS_H__

#include <dirent.h>
#include <fcntl.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef DT_DIR
#define DT_DIR 4
#endif

//
//    Search pid of running executable (forward match)
//
pid_t process_searchpid(const char *commname)
{
    DIR *procdp;
    struct dirent *dir;
    char fname[24];
    char comm[128];
    pid_t pid;
    pid_t ret = 0;
    size_t commlen = strlen(commname);

    procdp = opendir("/proc");
    if (!procdp)
        return 0;
    while ((dir = readdir(procdp))) {
        if (dir->d_type == DT_DIR) {
            pid = atoi(dir->d_name);
            if (pid > 2) {
                sprintf(fname, "/proc/%d/comm", pid);
                FILE *fp = fopen(fname, "r");
                if (fp) {
                    char *line = fgets(comm, sizeof(comm), fp);
                    fclose(fp);
                    if (!line)
                        continue;
                    comm[strcspn(comm, "\r\n")] = '\0';
                    if (!strncmp(comm, commname, commlen)) {
                        ret = pid;
                        break;
                    }
                }
            }
        }
    }
    closedir(procdp);
    return ret;
}

bool process_isRunning(const char *commname)
{
    return process_searchpid(commname) != 0;
}

void process_kill(const char *commname)
{
    pid_t pid;
    if ((pid = process_searchpid(commname)))
        kill(pid, SIGKILL);
}

void process_killall(const char *commname)
{
    pid_t pid;
    int max = 999;
    while ((pid = process_searchpid(commname)) && max-- > 0)
        kill(pid, SIGKILL);
}

bool process_start(const char *pname, const char *args, const char *home,
                   bool await)
{
    char filename[256];
    sprintf(filename, "%s/bin/%s", home != NULL ? home : ".", pname);
    if (!exists(filename))
        sprintf(filename, "%s/%s", home != NULL ? home : ".", pname);
    if (!exists(filename))
        sprintf(filename, "/mnt/SDCARD/.tmp_update/bin/%s", pname);
    if (!exists(filename))
        sprintf(filename, "/mnt/SDCARD/.tmp_update/%s", pname);
    if (!exists(filename))
        sprintf(filename, "/mnt/SDCARD/miyoo/app/%s", pname);
    if (!exists(filename))
        return false;

    char cmd[512];
    sprintf(cmd, "cd \"%s\"; %s %s %s", home != NULL ? home : ".", filename,
            args != NULL ? args : "", await ? "" : "&");
    system(cmd);

    return true;
}

int process_start_read_return(const char *cmdline, char *out_str, size_t out_size)
{
    char buffer[256];
    bool have_output = false, truncated = false;
    if (!out_str || out_size == 0)
        return -1;
    out_str[0] = '\0';

    FILE *pipe = popen(cmdline, "r");
    if (pipe == NULL) {
        fprintf(stderr, "Error executing command: %s\n", cmdline);
        return -1;
    }

    while (fgets(buffer, sizeof(buffer), pipe) != NULL) {
        size_t length = strcspn(buffer, "\r\n");
        if (length >= out_size || (length == sizeof(buffer) - 1 && !feof(pipe))) {
            truncated = true;
            continue;
        }
        memcpy(out_str, buffer, length);
        out_str[length] = '\0';
        have_output = true;
    }

    int read_error = ferror(pipe);
    int status = pclose(pipe);
    if (status != 0 || read_error || truncated || !have_output) {
        out_str[0] = '\0';
        return -1;
    }
    return 0;
}

#endif // PROCESS_H__
