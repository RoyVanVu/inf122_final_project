import sys
from gmae.gmae_core.main import main as cli_main

def main():
    print("Welcome to GuildQuest Mini-Adventure Environment")
    print("Please select mode:")
    print("1. CLI Mode")
    print("2. GUI Mode")
    
    while True:
        try:
            choice = input("Enter 1 or 2: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            sys.exit(0)
            
        if choice == "1":
            cli_main()
            break
        elif choice == "2":
            from gmae.gmae_gui_qt import run_gui
            run_gui()
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")

if __name__ == "__main__":
    main()