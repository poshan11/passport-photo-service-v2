#!/usr/bin/env python
"""
Google Photos Ordering Automation Script

This script automates the process of creating a photo order on Google Photos
using the Browser Use API.
"""
import argparse
from utils.browser_use_automation import run_google_photos_task, pause_task, resume_task, stop_task

def main():
    parser = argparse.ArgumentParser(description='Google Photos ordering automation')
    parser.add_argument('--action', choices=['run', 'pause', 'resume', 'stop'], 
                        default='run', help='Action to perform')
    parser.add_argument('--task-id', type=str, help='Task ID for pause/resume/stop actions')
    
    args = parser.parse_args()
    
    if args.action == 'run':
        print("Starting Google Photos ordering automation...")
        run_google_photos_task()
    elif args.task_id:
        if args.action == 'pause':
            pause_task(args.task_id)
        elif args.action == 'resume':
            resume_task(args.task_id)
        elif args.action == 'stop':
            stop_task(args.task_id)
    else:
        print("Error: Task ID is required for pause/resume/stop actions")
        parser.print_help()

if __name__ == "__main__":
    main()
