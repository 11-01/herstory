import shutil
import datetime
import os

def backup_db():
    if not os.path.exists("data.db"):
        print("❌ 未找到数据库文件 data.db")
        return

    time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_data_{time}.db"
    
    shutil.copy2("data.db", backup_file)
    print(f"✅ 备份成功：{backup_file}")

if __name__ == "__main__":
    backup_db()
