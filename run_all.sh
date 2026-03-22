#!/bin/bash

echo "🚀 PMDA 자동 다운로드를 시작합니다..."

# 위암 관련 약품
./pmda_downloader.py --drug "キイトルーダ"
./pmda_downloader.py --drug "オプジーボ"
./pmda_downloader.py --drug "エンハーツ"
./pmda_downloader.py --drug "サイラムザ"
./pmda_downloader.py --drug "ビロイ"

# 간암 관련 약품
./pmda_downloader.py --drug "テセントリク"
./pmda_downloader.py --drug "アバスチン"
./pmda_downloader.py --drug "イミフィンジ"
./pmda_downloader.py --drug "レンビマ"
./pmda_downloader.py --drug "ネクサバール"

# 폐암 관련 약품
./pmda_downloader.py --drug "タグリッソ"
./pmda_downloader.py --drug "アレセンサ"

# 별도 리스트
./pmda_downloader.py --drug "エンレスト"
./ctd_downloader.py --drug "エンレスト"

./pmda_downloader.py --drug "レボレード"
./pmda_downloader.py --drug "ジャカビ"
./pmda_downloader.py --drug "エクメット"
./pmda_downloader.py --drug "ケシンプタ"
./pmda_downloader.py --drug "イラリス"
./pmda_downloader.py --drug "タシグナ"

./pmda_downloader.py --drug "セムブリックス"
./ctd_downloader.py --drug "セムブリックス"

./pmda_downloader.py --drug "エクア"
./ctd_downloader.py --drug "エクア"

./pmda_downloader.py --drug "ゾレア"
./ctd_downloader.py --drug "ゾレア"

./pmda_downloader.py --drug "ファビハルタ"
./ctd_downloader.py --drug "ファビハルタ"
echo "✅ 모든 다운로드가 완료되었습니다!"
