import os
import shutil


def copy_history_files(source_dir, target_dir):
    # 确保目标文件夹存在
    os.makedirs(target_dir, exist_ok=True)

    # 遍历源文件夹下的一级子文件夹
    for subdir in next(os.walk(source_dir))[1]:
        # 构建需要保存文件的完整路径
        history_file = os.path.join(source_dir, subdir, 'history.json')
        lasterror=os.path.join(source_dir, subdir, f'{subdir}.txt')
        ql=os.path.join(source_dir, subdir, 'test.ql')

        if os.path.exists(history_file):
            target_file = os.path.join(target_dir, f'{subdir}-history.json')

            # 复制文件
            shutil.copy2(history_file, target_file)
            print(f'已复制: {history_file} 到 {target_file}')
        else:
            print(f'未找到: {history_file}')

        if os.path.exists(lasterror):

            target_file = os.path.join(target_dir, f'{subdir}.txt')

            # 复制文件
            shutil.copy2(lasterror, target_file)
            print(f'已复制: {lasterror} 到 {target_file}')
        else:
            print(f'未找到: {lasterror}')
        if os.path.exists(ql):
            target_file = os.path.join(target_dir, f'{subdir}-test.ql')

            # 复制文件
            shutil.copy2(ql, target_file)
            print(f'已复制: {ql} 到 {target_file}')
        else:
            print(f'未找到: {ql}')

if __name__ == '__main__':
    # 示例使用
    source_directory = ''  # 替换为实际源文件夹路径
    target_directory = ''  # 替换为实际目标文件夹路径
    copy_history_files(source_directory, target_directory)


