import os
import sqlite3

# Configuration
DB_PATH = 'mimikly.db'
PHOTO_FOLDER = os.path.join('uploads', 'photos')
VOICE_FOLDER = os.path.join('uploads', 'voices')

def migrate_existing_files():
    """Migrate existing files from disk to database blobs"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Starting migration of existing files...")
    
    # Migrate voice files
    print("\n--- Migrating Voice Files ---")
    c.execute('SELECT id, filename FROM voices')
    voices = c.fetchall()
    
    for voice_id, filename in voices:
        file_path = os.path.join(VOICE_FOLDER, filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    file_blob = f.read()
                
                # Check if 'file' column exists, add if not
                c.execute("PRAGMA table_info(voices)")
                columns = [col[1] for col in c.fetchall()]
                if 'file' not in columns:
                    c.execute('ALTER TABLE voices ADD COLUMN file BLOB')
                
                # Update the record with blob data
                c.execute('UPDATE voices SET file = ? WHERE id = ?', (file_blob, voice_id))
                print(f"✓ Migrated voice file: {filename}")
            except Exception as e:
                print(f"✗ Failed to migrate voice file {filename}: {e}")
        else:
            print(f"✗ Voice file not found on disk: {filename}")
    
    # Migrate photo files
    print("\n--- Migrating Photo Files ---")
    c.execute('SELECT id, filename FROM photos')
    photos = c.fetchall()
    
    for photo_id, filename in photos:
        file_path = os.path.join(PHOTO_FOLDER, filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    file_blob = f.read()
                
                # Check if 'data' column exists, add if not
                c.execute("PRAGMA table_info(photos)")
                columns = [col[1] for col in c.fetchall()]
                if 'data' not in columns:
                    c.execute('ALTER TABLE photos ADD COLUMN data BLOB')
                
                # Update the record with blob data
                c.execute('UPDATE photos SET data = ? WHERE id = ?', (file_blob, photo_id))
                print(f"✓ Migrated photo file: {filename}")
            except Exception as e:
                print(f"✗ Failed to migrate photo file {filename}: {e}")
        else:
            print(f"✗ Photo file not found on disk: {filename}")
    
    conn.commit()
    # --- Checking Video Files ---
    print("\n--- Checking Video Files ---")
    existing_filenames = set()
    c.execute("SELECT filename FROM videos")
    for row in c.fetchall():
        existing_filenames.add(row[0])
    VIDEO_FOLDER = os.path.join('uploads', 'videos')
    for filename in os.listdir(VIDEO_FOLDER):
        if filename.endswith(".mp4") and filename not in existing_filenames:
            video_path = os.path.join(VIDEO_FOLDER, filename)
            c.execute("INSERT INTO videos (name, filename) VALUES (?, ?)", (filename, filename))
            print(f"✓ Added missing video: {filename}")
    conn.commit()
    conn.close()
    print("\n--- Migration Complete ---")

def check_current_status():
    """Check current database status"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Current Database Status:")
    
    # Check voices table
    c.execute("PRAGMA table_info(voices)")
    voice_columns = [col[1] for col in c.fetchall()]
    print(f"Voices table columns: {voice_columns}")
    
    if 'file' in voice_columns:
        c.execute('SELECT COUNT(*) FROM voices WHERE file IS NOT NULL')
        voices_with_blob = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM voices')
        total_voices = c.fetchone()[0]
        print(f"Voice files with blob data: {voices_with_blob}/{total_voices}")
    
    # Check photos table
    c.execute("PRAGMA table_info(photos)")
    photo_columns = [col[1] for col in c.fetchall()]
    print(f"Photos table columns: {photo_columns}")
    
    if 'data' in photo_columns:
        c.execute('SELECT COUNT(*) FROM photos WHERE data IS NOT NULL')
        photos_with_blob = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM photos')
        total_photos = c.fetchone()[0]
        print(f"Photo files with blob data: {photos_with_blob}/{total_photos}")
    
    # Check videos table
    c.execute("PRAGMA table_info(videos)")
    video_columns = [col[1] for col in c.fetchall()]
    print(f"Videos table columns: {video_columns}")
    c.execute('SELECT COUNT(*) FROM videos')
    total_videos = c.fetchone()[0]
    print(f"Total video records in DB: {total_videos}")
    c.execute("SELECT filename FROM videos LIMIT 3")
    sample_videos = c.fetchall()
    print("Sample videos from DB:", [v[0] for v in sample_videos])
    
    conn.close()

if __name__ == '__main__':
    print("Database Migration Tool")
    print("======================")
    
    # First, check current status
    check_current_status()
    
    # Ask user if they want to proceed with migration
    response = input("\nDo you want to migrate existing files to database blobs? (y/n): ")
    
    if response.lower() in ['y', 'yes']:
        migrate_existing_files()
        print("\nChecking status after migration:")
        check_current_status()
    else:
        print("Migration cancelled.")