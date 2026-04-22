var socket = io();
const videoImg = document.getElementById('video_feed');
const messageOverlay = document.getElementById('message-overlay');
let isPlaying = false;

// 音声オブジェクトはここでは定義せず、再生直前に作ります
socket.on('vulcan_detected', function() {
    if (isPlaying) return;
    isPlaying = true;

    console.log("Vulcan detected! Forcing connection reset...");

    // 1. 動画を止めるだけでなく、srcを「完全に別の無害なもの」に変えて、
    // 進行中のストリーム通信を強制的に切断させます
    videoImg.src = "about:blank"; 
    messageOverlay.style.display = "block";

    // 2. 0.5秒だけ待って、通信路が空くのを待つ（ここがミソです）
    setTimeout(() => {
        const audio = new Audio('/static/vulcan.mp3?t=' + Date.now()); // キャッシュ回避
        audio.play().then(() => {
            audio.onended = () => {
                messageOverlay.style.display = "none";
                videoImg.src = "/video_feed"; // 再開
                isPlaying = false;
            };
        }).catch(e => {
            console.error("Play error:", e);
            messageOverlay.style.display = "none";
            videoImg.src = "/video_feed";
            isPlaying = false;
        });
    }, 500); 
});