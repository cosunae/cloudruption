#include <mpi.h>
#include <stdio.h>

/*
* This code is adapted from an example at:
* http://brokestream.com/procstat.html
*/

int get_cpu_id()
{
    /* Get the the current process' stat file from the proc filesystem */
    FILE* procfile = fopen("/proc/self/stat", "r");
    long to_read = 8192;
    char buffer[to_read];
    int read = fread(buffer, sizeof(char), to_read, procfile);
    fclose(procfile);

    // Field with index 38 (zero-based counting) is the one we want
    char* line = strtok(buffer, " ");
    for (int i = 1; i < 38; i++)
    {
        line = strtok(NULL, " ");
    }

    line = strtok(NULL, " ");
    int cpu_id = atoi(line);
    return cpu_id;
}


int main(int argc, char** argv) {
    // Initialize the MPI environment
    MPI_Init(NULL, NULL);

    // Get the number of processes
    int world_size;
    char processor_name[MPI_MAX_PROCESSOR_NAME];

    MPI_Comm_size(MPI_COMM_WORLD, &world_size);

    // Get the rank of the process
    int world_rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);

    // Get the name of the processor
    int name_len;
    MPI_Get_processor_name(processor_name, &name_len);

    int cpu_id = get_cpu_id();
    // Print off a hello world message
    printf("Hello world from processor %s, rank %d, cpu id %d, out of %d processors\n",
           processor_name, world_rank, cpu_id, world_size);

    // Finalize the MPI environment.
    MPI_Finalize();
}

