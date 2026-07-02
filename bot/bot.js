const { launch, getStream } = require("puppeteer-stream");
const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const meetUrl = args[0];
const outputAudio = args[1] || "meeting_audio.webm";
const outputParticipants = args[2] || "participants.json";
const durationSeconds = parseInt(args[3] || "60");

if (!meetUrl) {
    console.error("Usage: node bot.js <meet_url> <output_audio> <output_json> <duration_sec>");
    process.exit(1);
}

async function startBot() {
    console.log(`[BOT] Starting bot for ${meetUrl}`);
    
    // Launch headless browser with extension to capture audio
    const browser = await launch({
        headless: "new",
        defaultViewport: { width: 1280, height: 720 },
        args: [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            "--mute-audio" // Prevent the host from hearing the bot's own echo
        ]
    });
    
    const page = await browser.newPage();
    
    // Deny permissions explicitly so it doesn't prompt
    const context = browser.defaultBrowserContext();
    await context.overridePermissions('https://meet.google.com', []);

    console.log("[BOT] Navigating to Google Meet...");
    await page.goto(meetUrl, { waitUntil: 'networkidle2' });

    // Wait for the name input or join button
    try {
        console.log("[BOT] Looking for name input...");
        await page.waitForSelector('input[type="text"]', { timeout: 15000 });
        await page.type('input[type="text"]', "MeetTrack AI");
        
        // Find and click the "Ask to join" or "Join" button
        const joinButton = await page.evaluateHandle(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            return buttons.find(b => b.innerText.includes('Ask to join') || b.innerText.includes('Join now') || b.innerText.includes('Join'));
        });
        
        if (joinButton) {
            await joinButton.click();
            console.log("[BOT] Clicked Ask to Join. Waiting for admission from host...");
        } else {
            console.log("[BOT] Could not find the Join button by text.");
        }
    } catch (e) {
        console.log("[BOT] Could not find name input. Might be a different UI layout or already logged in.");
    }

    // Wait until we are actually in the meeting by looking for the microphone/camera control buttons
    console.log("[BOT] Waiting to be admitted...");
    try {
        await page.waitForFunction(() => {
            return document.querySelectorAll('button[aria-label*="microphone"], button[aria-label*="camera"], button[aria-label*="Microphone"], button[aria-label*="Camera"]').length > 0;
        }, { timeout: 120000 }); // Wait up to 2 mins for host to admit
        console.log("[BOT] Joined meeting successfully!");
    } catch(e) {
        console.error("[BOT] Failed to join meeting (timeout waiting for admission). Exiting.");
        await browser.close();
        process.exit(1);
    }

    // Start audio recording
    console.log("[BOT] Starting audio recording...");
    const stream = await getStream(page, { audio: true, video: false });
    const file = fs.createWriteStream(outputAudio);
    stream.pipe(file);

    // Open participants sidebar
    try {
        const peopleBtn = await page.evaluateHandle(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            return buttons.find(b => b.getAttribute('aria-label') && (b.getAttribute('aria-label').toLowerCase().includes('people') || b.getAttribute('aria-label').toLowerCase().includes('participant')));
        });
        if (peopleBtn) {
            await peopleBtn.click();
            console.log("[BOT] Opened participants sidebar.");
        }
    } catch(e) {
        console.log("[BOT] Failed to open participants sidebar.");
    }

    const participants = new Set();
    
    // Scrape participants every 5 seconds
    const scrapeInterval = setInterval(async () => {
        try {
            const names = await page.evaluate(() => {
                // Google Meet participant names are usually in role="listitem" spans or divs
                const elements = document.querySelectorAll('[role="listitem"] span[dir="auto"], [role="listitem"] div[dir="auto"]');
                return Array.from(elements).map(e => e.innerText).filter(n => n && n !== "You" && !n.includes("Presentation"));
            });
            names.forEach(n => participants.add(n));
            
            // Save to JSON continually
            fs.writeFileSync(outputParticipants, JSON.stringify(Array.from(participants), null, 2));
        } catch(e) {}
    }, 5000);

    // Record for the specified duration (e.g., 60 seconds for testing)
    console.log(`[BOT] Recording for ${durationSeconds} seconds...`);
    await new Promise(r => setTimeout(r, durationSeconds * 1000));
    
    console.log("[BOT] Meeting finished. Saving data...");
    clearInterval(scrapeInterval);
    stream.destroy();
    file.close();
    await browser.close();
    console.log("[BOT] Disconnected gracefully.");
}

startBot().catch(err => {
    console.error("[BOT] Fatal Error:", err);
    process.exit(1);
});
