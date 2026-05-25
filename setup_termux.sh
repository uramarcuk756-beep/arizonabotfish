#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  ArizonaFish Bot — установка в Termux и сборка APK
#  Запускай по шагам! Каждый шаг может занять время.
# ============================================================

echo "=== Шаг 1: обновляем пакеты ==="
pkg update -y && pkg upgrade -y

echo "=== Шаг 2: устанавливаем зависимости системы ==="
pkg install -y python python-dev gcc binutils cmake \
    zip unzip tar git wget curl \
    libffi-dev openssl-dev libjpeg-turbo-dev \
    zlib-dev openjdk-17

echo "=== Шаг 3: pip зависимости ==="
pip install --upgrade pip
pip install buildozer cython virtualenv

echo "=== Шаг 4: переходим в папку проекта ==="
# Скопируй main.py и buildozer.spec сюда:
mkdir -p ~/arizonafish
cp main.py ~/arizonafish/
cp buildozer.spec ~/arizonafish/
cd ~/arizonafish

echo "=== Шаг 5: собираем APK (займёт 30-90 минут!) ==="
echo "!!! Телефон должен не спать всё это время !!!"
buildozer android debug

echo ""
echo "=== ГОТОВО! ==="
echo "APK лежит здесь:"
ls -lh bin/*.apk 2>/dev/null || echo "Смотри в папку bin/"
echo ""
echo "Установить APK:"
echo "  adb install bin/*.apk"
echo "  или просто открой файл из файлового менеджера"
