#!/usr/bin/env python3
"""语稿智能整理系统 - 命令行入口"""

import argparse
import sys
from pathlib import Path
from script_refine import ScriptRefiner


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="语稿智能整理系统 - 自动将语音识别文本转换为高质量文稿",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成完整版
  python main.py -i input.txt -o output/ -m full
  
  # 生成会议纪要
  python main.py -i input.txt -o output/ -m summary
  
  # 同时生成完整版和会议纪要
  python main.py -i input.txt -o output/ -m both
  
  # 使用自定义配置
  python main.py -i input.txt -c config_local.yaml -m full
        """
    )
    
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="输入文件路径（支持 .txt, .md）"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="输出目录（默认: ./output）"
    )
    
    parser.add_argument(
        "-m", "--mode",
        choices=["full", "summary", "both"],
        default="full",
        help="输出模式: full=完整版, summary=会议纪要, both=两者（默认: full）"
    )
    
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="配置文件路径（默认: config.yaml）"
    )
    
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="不显示进度条"
    )
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not Path(args.input).exists():
        print(f"❌ 错误: 输入文件不存在: {args.input}")
        sys.exit(1)
    
    try:
        # 初始化系统
        print("🚀 初始化语稿智能整理系统...")
        refiner = ScriptRefiner(config_path=args.config)
        
        # 处理文件
        results = refiner.process(
            input_path=args.input,
            output_mode=args.mode,
            output_dir=args.output,
            show_progress=not args.no_progress
        )
        
        # 输出结果
        print("\n" + "="*50)
        print("✅ 处理完成！")
        print("="*50)
        for format_type, filepath in results.items():
            print(f"  {format_type}: {filepath}")
        print("="*50)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

