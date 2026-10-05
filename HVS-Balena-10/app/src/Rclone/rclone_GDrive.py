import pathlib
import subprocess
from src.configs.configs import config

class rclone_upload:
    def copy_now():

        OUT_DIR: pathlib.Path = pathlib.Path(__file__).parents[2] / "captures/"
        SYNC_SRC_DIR: str = str(OUT_DIR.absolute())

        REMOTE_PREFIX: str = "gdrive"
        SYNC_DEST_DIR: str = f"{config.BRANCH}/images/"

        pathlib.Path(OUT_DIR).mkdir(parents=True, exist_ok=True)


        command= ["rclone","copy",SYNC_SRC_DIR,f"{REMOTE_PREFIX}:{SYNC_DEST_DIR}","--update"]

        try:
            print(f"Executing command: {' '.join(command)}")
            result = subprocess.run(command, check=True)
            print(f"Command completed successfully with return code {result.returncode}")
        except subprocess.CalledProcessError as e:
            print(f"Command failed with non-zero exit code: {e.returncode}. Command: {' '.join(command)}")
        
        return

      

