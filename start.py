import subprocess
import os
import signal
import threading
import logging
import argparse
from utils.logger_utils import setup_logger
import datetime
import multiprocessing
from server import main
import random
import select
import time


# Set up logging
log_dir = None
start_team_logger = None

def run_server_script(args):
    rpc_port = args.rpc_port
    if args.use_random_rpc_port or args.use_different_rpc_port:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            rpc_port = str(s.getsockname()[1])
        start_team_logger.debug(f"Using random port: {rpc_port}")
    # Define a wrapper function to pass the arguments to the main function
    def server_main():
        import sys
        # Reset signal handlers to default in the child process
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        sys.argv = ['server.py', '--rpc-port', str(rpc_port), '--log-dir', log_dir]
        if args.disable_log_file:
            sys.argv += ['--disable-log-file']
        main()

    # Start the main function as a new process
    process = multiprocessing.Process(target=server_main)
    process.start()
    return process, rpc_port

def run_start_script(args, rpc_port):
    # Start the start.sh script in its own directory as a new process group
    arguments = ['bash']
    if args.player or args.coach or args.goalie:
        if args.debug:
            arguments += ['start-debug-agent.sh', '--coach' if args.coach else '--goalie' if args.goalie else '--player']
        else:
            arguments += ['start-agent.sh', '--coach' if args.coach else '--goalie' if args.goalie else '--player']
    else:
        arguments += ['start.sh' if not args.debug else 'start-debug.sh']
        
    arguments += ['-t', args.team_name, 
         '--rpc-port', rpc_port, '--rpc-type', 'grpc', 
         '-p', args.server_port, '-h', args.server_host]
        
    process = subprocess.Popen(
        arguments,
        cwd='scripts/proxy',  # Corrected directory to where start.sh is located
        preexec_fn=os.setsid,  # Create a new session and set the process group ID
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT  # Capture stderr and redirect it to stdout
    )
    return process

stop_thread = threading.Event()

def stream_output_to_file(process, name, args):
    # Stream output from the process and log it to a file with the given name
    f = None if args.disable_log_file else open(f"{log_dir}/{name}.log", "a")
    while not stop_thread.is_set():
        if select.select([process.stdout], [], [], 1)[0]:
            output = process.stdout.readline()
            if output:
                if f:
                    f.write(output.decode())
                    f.flush()
                else:
                    print(output.decode())
            else:
                break
    process.stdout.close()
    if f:
        f.close()
    
def kill_process_group(processes):
    for process in processes:
        try:
            start_team_logger.debug(f"Killing process group with PID: {process.pid}")
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)  # Send SIGTERM to the process group
        except ProcessLookupError:
            pass  # The process might have already exited

def kill_rpc_server_process(processes):
    for process in processes:
        try:
            start_team_logger.debug(f"Killing process with PID: {process.pid}")
            os.kill(process.pid, signal.SIGTERM)  # Send SIGTERM to the specific process
        except ProcessLookupError:
            pass  # The process might have already exited

def check_rcssserver_process(args):
    import psutil 
    for conn in psutil.net_connections(kind='inet'):
        server_host_ip = args.server_host if args.server_host != 'localhost' else '0.0.0.0'
        # start_team_logger.debug(f"Checking connection: {conn.laddr.ip=}, {conn.laddr.port=}, {args.server_host=}, {server_host_ip=}")
        if conn.laddr.port == int(args.server_port) and conn.laddr.ip == server_host_ip:
            # start_team_logger.debug(f"Found rcssserver process with PID: {conn.pid}")
            return True
    return False

def check_args(args):
    if args.team_name != 'CLS' and args.use_random_name:
        raise ValueError("Cannot use both --team_name and --use-random-name")
    if args.rpc_port != '50051' and args.use_random_rpc_port:
        raise ValueError("Cannot use both --rpc-port and --use-random-rpc-port")
    if args.rpc_port != '50051' and args.use_different_rpc_port:
        raise ValueError("Cannot use both --rpc-port and --use-different-rpc-port")
    if args.use_random_rpc_port and args.use_different_rpc_port:
        raise ValueError("Cannot use both --use-random-port and --use-different-rpc-port")
    if args.player and args.coach:
        raise ValueError("Cannot use both --player and --coach")
    if args.player and args.goalie:
        raise ValueError("Cannot use both --player and --goalie")
    if args.coach and args.goalie:
        raise ValueError("Cannot use both --coach and --goalie")
    if (args.player or args.coach or args.goalie) and args.use_different_rpc_port:
        raise ValueError("Cannot use --player, --coach, or --goalie with --use-different-rpc-port")
    if args.disable_log_file and args.log_dir:
        raise ValueError("Cannot use both --disable-log-file and --log-dir")
        

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Run server and team scripts.')
    parser.add_argument('-t', '--team_name', required=False, help='The name of the team', default='CLS')
    parser.add_argument('--rpc-port', required=False, help='The port of the rpc server', default='50051')
    parser.add_argument('-d', '--debug', required=False, help='Enable debug mode for agents', default=False, action='store_true')
    parser.add_argument('--use-random-rpc-port', required=False, help='Use a random port for the rpc server', default=False, action='store_true')
    parser.add_argument('--use-random-name', required=False, help='Use a random team name', default=False, action='store_true')
    parser.add_argument('--use-different-rpc-port', required=False, help='Use a different port for the rpc server', default=False, action='store_true')
    parser.add_argument('--server-host', required=False, help='The host of the robocup soccer server', default='localhost')
    parser.add_argument('--server-port', required=False, help='The port of the robocup soccer server', default='6000')
    parser.add_argument('--auto-close-rpc-server', required=False, help='Close the server after finished agent processing', default=False, action='store_true')
    parser.add_argument('--player', required=False, help='Run one agent proxy as player', default=False, action='store_true')
    parser.add_argument('--coach', required=False, help='Run one agent proxy as coach', default=False, action='store_true')
    parser.add_argument('--goalie', required=False, help='Run one agent proxy as goalie', default=False, action='store_true')
    parser.add_argument('--disable-log-file', required=False, help='Disable logging to a file', default=False, action='store_true')
    parser.add_argument('--log-dir', required=False, help='The directory to store logs', default=None)
    args = parser.parse_args()
    
    check_args(args)
    
    # Set up logging
    if not args.log_dir:
        log_dir = os.path.join(os.getcwd(), 'logs', f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{random.randint(100000, 999999)}")
    else:
        log_dir = os.path.join(args.log_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{random.randint(100000, 999999)}")
    start_team_logger = setup_logger('start-team', log_dir, console_level=logging.DEBUG, file_level=logging.DEBUG if not args.disable_log_file else None, console_format_str='%(message)s')

    start_team_logger.debug(f"Arguments: {args=}")
    
    def signal_handler(sig, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        if args.use_random_name:
            import random
            import string
            args.team_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        
        #Check that rcssserver is running for 10 seconds 
        start_time = time.time()
        start_team_logger.debug("Checking for rcssserver process...")
        time_th = 10
        while not check_rcssserver_process(args):
            if time.time() - start_time > time_th:
                raise Exception("rcssserver process not found.")
            time.sleep(1)
        start_team_logger.debug("rcssserver process found.")


        # Run the server.py script first
        all_server_processes = []
        all_start_processes = []
        if args.use_different_rpc_port:
            for i in range(13):
                server_process, rpc_port = run_server_script(args)
                all_server_processes.append(server_process)
                start_team_logger.debug(f"Started server.py process with PID: {all_server_processes[-1].pid}")
                args.goalie, args.coach, args.player = False, False, False
                args.player = False
                if i == 0:
                    args.goalie = True
                    time.sleep(1)
                elif i == 12:
                    args.coach = True
                else:
                    args.player = True
                
                # Run the start.sh script after server.py with the given arguments
                all_start_processes.append(run_start_script(args, rpc_port))
                start_team_logger.debug(f"Started start.sh process with PID: {all_start_processes[-1].pid} with team name {args=} and rpc port {rpc_port}")
        else:
            server_process, rpc_port = run_server_script(args)
            all_server_processes.append(server_process)
            start_team_logger.debug(f"Started server.py process with PID: {all_server_processes[-1].pid}")
            
            # Run the start.sh script after server.py with the given arguments
            all_start_processes.append(run_start_script(args, rpc_port))
            start_team_logger.debug(f"Started start.sh process with PID: {all_start_processes[-1].pid} with team name {args=} and rpc port {rpc_port}")

        # Monitor both processes and log their outputs
        start_team_logger.debug("Monitoring processes...")
    
        
        start_threads: list[threading.Thread] = []
        for i, start_process in enumerate(all_start_processes):
            start_threads.append(threading.Thread(target=stream_output_to_file, args=(start_process, 'proxy' if len(all_start_processes) == 1 else f'porxy_{i}', args)))
            start_threads[-1].start()
        
        # Wait for both threads to finish
        for start_thread in start_threads:
            start_thread.join()
        start_team_logger.debug("agents has been exited.")
        
        if args.auto_close_rpc_server:
            start_team_logger.debug("Closing rpc server ...")
            kill_rpc_server_process(all_server_processes)
            start_team_logger.debug("rpc Server has been closed.")
            
        # wait for server process to finish
        for server_process in all_server_processes:
            server_process.join()
        start_team_logger.debug("server.py has finished.")
        
        start_team_logger.info("Both processes have exited.")
    except KeyboardInterrupt:
        start_team_logger.info('Received signal to terminate. Cleaning up...')
        # Perform cleanup operations here
        kill_rpc_server_process(all_server_processes)
        for server_process in all_server_processes:
            server_process.join()
            start_team_logger.debug(f"server.py ended with PID: {server_process.pid}")
            
        start_team_logger.debug("All server processes have finished.")
        
        kill_process_group(all_start_processes)
        for start_process in all_start_processes:
            start_process.wait()
            start_team_logger.debug(f"start.sh ended with PID: {start_process.pid}")
        
        start_team_logger.debug("All start processes have finished.")
        
        stop_thread.set()
    
        start_team_logger.debug("Waiting for start threads to finish...")
        for start_thread in start_threads:
            start_thread.join()
        
        start_team_logger.debug("Start threads have finished.")
        
        start_team_logger.info('All processes have been killed.')
    finally:
        # Ensure all processes are killed on exit
        start_team_logger.debug("Final cleanup...")
        kill_rpc_server_process(all_server_processes)
        kill_process_group(all_start_processes)
