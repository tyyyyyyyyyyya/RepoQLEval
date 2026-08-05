import os
import shutil


def copy_history_files(source_dir, target_dir):
    os.makedirs(target_dir, exist_ok=True)

    for subdir in next(os.walk(source_dir))[1]:
        history_file = os.path.join(source_dir, subdir, 'history.json')
        lasterror=os.path.join(source_dir, subdir, f'{subdir}.txt')
        ql=os.path.join(source_dir, subdir, 'test.ql')

        if os.path.exists(history_file):
            target_file = os.path.join(target_dir, f'{subdir}-history.json')

            shutil.copy2(history_file, target_file)
            print(f'Copied:{history_file} to {target_file}')
        else:
            print(f'Not found: {history_file}')

        if os.path.exists(lasterror):

            target_file = os.path.join(target_dir, f'{subdir}.txt')

            shutil.copy2(lasterror, target_file)
            print(f'Copied: {lasterror} to {target_file}')
        else:
            print(f'Not found: {lasterror}')
        if os.path.exists(ql):
            target_file = os.path.join(target_dir, f'{subdir}-test.ql')

            shutil.copy2(ql, target_file)
            print(f'Copied: {ql} to {target_file}')
        else:
            print(f'Not found: {ql}')

if __name__ == '__main__':
    source_directory = ''
    target_directory = ''
    copy_history_files(source_directory, target_directory)


