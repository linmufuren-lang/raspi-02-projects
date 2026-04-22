const socket = io();
const feed = document.getElementById('feed');
const overlay = document.getElementById('overlay');
const audio = new Audio('/static/vulcan.mp3');
let isLocked = false;

// ページ読み込み時に音声をロード
audio.load();

// ブラウザの音出し制限を解除する儀式
window.addEventListener('click', () => {
    audio.play().then(() => { audio.pause(); audio.currentTime = 0; });
}, { once: true });

socket.on('vulcan_detected', function() {
    if (isLocked) return;
    isLocked = true;

    console.log("Detected! Pausing video for audio...");

    // 1. 動画ストリームを「完全に」切断（about:blankにするのが最も効果的）
    const originalSrc = feed.src;
    feed.src = "about:blank"; 
    overlay.style.display = "block";

    // 2. 0.5秒待ってから音声をリクエスト（サーバーの負荷が下がるのを待つ）
    setTimeout(() => {
        audio.play().then(() => {
            audio.onended = () => {
                // 3. 再生終了後に復帰
                overlay.style.display = "none";
                feed.src = originalSrc;
                isLocked = false;
            };
        }).catch(e => {
            console.error(e);
            overlay.style.display = "none";
            feed.src = originalSrc;
            isLocked = false;
        });
    }, 500); 
});