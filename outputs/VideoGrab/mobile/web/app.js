const $ = (id) => document.getElementById(id);
const query = new URLSearchParams(location.search);
let publicMode = query.get("mode") === "public";
let token = query.get("token") || localStorage.getItem("videograb-token") || "";
if (query.get("token")) {
  localStorage.setItem("videograb-token", token);
  history.replaceState({}, "", location.pathname);
}

const text = {
  zh: {eyebrow:"局域网媒体工作台",headline:"粘贴链接，<br><em>保存你需要的内容。</em>",subtitle:"电脑负责处理，iPhone 负责控制。文件只在你的设备和当前 Wi‑Fi 中流转。",urlLabel:"媒体链接",paste:"粘贴",analyze:"解析链接",rights:"继续即表示你拥有该内容或已获得下载授权。",analysisComplete:"解析完成",output:"输出内容",video:"视频",cover:"封面",quality:"视频画质",best:"最佳可用",startDownload:"开始下载",activeTask:"当前任务",preparing:"正在准备…",cancel:"取消任务",connected:"电脑服务已连接",pair:"显示配对码",pairTitle:"连接 iPhone",scanTitle:"扫描二维码打开",sameWifi:"电脑与 iPhone 连接同一个 Wi‑Fi",scan:"使用相机扫描二维码",addHome:"在 Safari 分享菜单选择“添加到主屏幕”",settings:"设置",experience:"显示与连接",language:"界面语言",languageHelp:"中文 / English",fontSize:"字号大小",fontHelp:"同步调整整个界面",browser:"登录状态",browserHelp:"使用电脑浏览器的登录状态",install:"添加到主屏幕",needPair:"需要重新配对",needPairHelp:"请在电脑上打开 VideoGrab Mobile，扫描页面中的二维码。",analyzing:"正在解析媒体…",downloadReady:"任务已创建",downloadFile:"存到 iPhone",installHint:"请在 Safari 中点击分享，再选择“添加到主屏幕”。",networkError:"无法连接电脑，请确认服务仍在运行且处于同一 Wi‑Fi。"},
  en: {eyebrow:"LOCAL MEDIA WORKSPACE",headline:"Paste a link.<br><em>Keep what you need.</em>",subtitle:"Your computer processes. Your iPhone controls. Files stay on your devices and current Wi-Fi.",urlLabel:"Media link",paste:"Paste",analyze:"Analyze link",rights:"By continuing, you confirm that you own or are authorized to download this content.",analysisComplete:"Analysis complete",output:"Output",video:"Video",cover:"Cover",quality:"Video quality",best:"Best available",startDownload:"Start download",activeTask:"Active task",preparing:"Preparing…",cancel:"Cancel task",connected:"Computer connected",pair:"Show pairing code",pairTitle:"CONNECT IPHONE",scanTitle:"Scan to open",sameWifi:"Connect the computer and iPhone to the same Wi-Fi",scan:"Scan the QR code with Camera",addHome:"In Safari Share, choose Add to Home Screen",settings:"SETTINGS",experience:"Display & connection",language:"Language",languageHelp:"中文 / English",fontSize:"Text size",fontHelp:"Scale the entire interface",browser:"Signed-in browser",browserHelp:"Use browser session from the computer",install:"Add to Home Screen",needPair:"Pairing required",needPairHelp:"Open VideoGrab Mobile on the computer and scan the QR code.",analyzing:"Analyzing media…",downloadReady:"Download created",downloadFile:"Save to iPhone",installHint:"In Safari, tap Share and choose Add to Home Screen.",networkError:"Cannot reach the computer. Keep the service open and use the same Wi-Fi."}
};

const publicText = {
  zh:{eyebrow:"公开视频工作台",subtitle:"从任意设备粘贴媒体链接。处理由在线的 VideoGrab 客户端完成，文件将在 2 小时后自动清理。",connected:"公开网页已连接",notice:"公开模式：每位访客每分钟最多解析 10 次、每小时最多创建 3 个任务；不读取电脑浏览器登录状态。"},
  en:{eyebrow:"PUBLIC MEDIA WORKSPACE",subtitle:"Paste a media link from any device. The online VideoGrab client processes it and removes files automatically after 2 hours.",connected:"Public workspace connected",notice:"Public mode: up to 10 analyses per minute and 3 download jobs per hour per visitor. Browser sessions are disabled."}
};

let lang = localStorage.getItem("videograb-lang") || "zh";
let currentJob = null;
let pollTimer = null;
let installPrompt = null;

function t(key){ return (text[lang] || text.zh)[key] || key; }
function applyLanguage(){
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const value = t(el.dataset.i18n);
    if (value.includes("<")) el.innerHTML = value; else el.textContent = value;
  });
  $("languageSelect").value = lang;
  applyPublicMode();
}
function applyPublicMode(){
  if(!publicMode)return;
  const copy=publicText[lang]||publicText.zh;
  document.body.classList.add("public-mode");
  document.querySelector(".eyebrow").textContent=copy.eyebrow;
  document.querySelector(".hero p").textContent=copy.subtitle;
  document.querySelector(".connection [data-i18n='connected']").textContent=copy.connected;
  $("publicNotice").textContent=copy.notice;
  $("publicNotice").classList.remove("hidden");
  $("pairButton").classList.add("hidden");
  $("browserSetting").classList.add("hidden");
  $("browserSelect").value="";
}
function toast(message){
  const el=$("toast"); el.textContent=message; el.classList.add("show");
  clearTimeout(el._timer); el._timer=setTimeout(()=>el.classList.remove("show"),2600);
}
function show(id){ $(id).classList.remove("hidden"); $(id).setAttribute("aria-hidden","false"); }
function hide(id){ $(id).classList.add("hidden"); $(id).setAttribute("aria-hidden","true"); }
function authHeaders(json=true){ const h={"X-VideoGrab-Token":token}; if(json) h["Content-Type"]="application/json"; return h; }
async function api(path, options={}){
  options.headers={...authHeaders(options.body!==undefined),...(options.headers||{})};
  const response=await fetch(path,options);
  let body={}; try{body=await response.json();}catch{}
  if(response.status===401){show("pairingGate");throw new Error("pairing_required");}
  if(!response.ok) throw new Error(body.error||`HTTP ${response.status}`);
  return body;
}
function setBusy(button,busy,label){ button.disabled=busy; button.dataset.original ||= button.querySelector("span")?.textContent || button.textContent; if(button.querySelector("span")) button.querySelector("span").textContent=busy?label:button.dataset.original; }
function formatBytes(n){ if(n<1024*1024)return `${Math.max(1,Math.round(n/1024))} KB`; return `${(n/1024/1024).toFixed(1)} MB`; }

async function connect(){
  if(!token){show("pairingGate");return;}
  try{
    const config=await api("/api/config",{headers:authHeaders(false)});
    publicMode=Boolean(config.publicMode)||publicMode;
    applyPublicMode();
    hide("pairingGate");
    $("shareUrl").textContent=config.shareUrl;
    $("qrImage").src=`/api/qr.png?token=${encodeURIComponent(token)}&v=${Date.now()}`;
    await refreshJobs();
  }catch(error){ if(error.message!=="pairing_required")toast(t("networkError")); }
}

async function analyze(){
  const url=$("urlInput").value.trim(); if(!url){toast(t("urlLabel"));return;}
  setBusy($("analyzeButton"),true,t("analyzing"));
  try{
    const data=await api("/api/analyze",{method:"POST",body:JSON.stringify({url,browser:publicMode?"":$("browserSelect").value})});
    $("mediaTitle").textContent=data.title;
    $("mediaMeta").textContent=`${data.duration}  ·  ${data.formatCount} formats`;
    $("sourceBadge").textContent=data.source.toUpperCase();
    $("thumbnail").src=data.thumbnail || "/logo.png";
    $("qualitySelect").innerHTML=`<option value="0">${t("best")}</option>`+data.qualities.map(q=>`<option value="${q}">${q}p</option>`).join("");
    show("analysisCard"); $("analysisCard").scrollIntoView({behavior:"smooth",block:"start"});
  }catch(error){toast(error.message);}finally{setBusy($("analyzeButton"),false,t("analyzing"));}
}

async function download(){
  try{
    const payload={url:$("urlInput").value.trim(),video:$("videoOption").checked,cover:$("coverOption").checked,mp3:$("mp3Option").checked,quality:$("qualitySelect").value,browser:publicMode?"":$("browserSelect").value,language:lang};
    currentJob=await api("/api/download",{method:"POST",body:JSON.stringify(payload)});
    show("taskCard"); renderJob(currentJob); startPolling(); $("taskCard").scrollIntoView({behavior:"smooth",block:"start"}); toast(t("downloadReady"));
  }catch(error){toast(error.message);}
}
function renderJob(job){
  currentJob=job; const progress=Number(job.progress||0); $("progressValue").textContent=`${progress.toFixed(0)}%`; $("progressBar").style.width=`${progress}%`; $("taskTitle").textContent=job.title||t("preparing"); $("taskMessage").textContent=job.message||"—";
  const done=["complete","error","cancelled"].includes(job.status); $("cancelButton").classList.toggle("hidden",done);
  const files=job.files||[]; $("fileList").innerHTML=files.map(file=>`<a class="file-link" href="/api/file?job=${encodeURIComponent(job.id)}&file=${encodeURIComponent(file.id)}&token=${encodeURIComponent(token)}"><span>${escapeHtml(file.name)} · ${formatBytes(file.size)}</span><b>${t("downloadFile")}</b></a>`).join("");
}
function escapeHtml(value){return String(value).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));}
async function refreshJobs(){
  const data=await api("/api/jobs",{headers:authHeaders(false)}); if(data.jobs.length){const active=data.jobs.find(j=>["queued","downloading","processing"].includes(j.status))||data.jobs[0]; if(active){show("taskCard");renderJob(active);if(!["complete","error","cancelled"].includes(active.status))startPolling();}}
}
function startPolling(){clearInterval(pollTimer);pollTimer=setInterval(async()=>{try{const data=await api("/api/jobs",{headers:authHeaders(false)});const job=data.jobs.find(j=>j.id===currentJob?.id);if(job){renderJob(job);if(["complete","error","cancelled"].includes(job.status)){clearInterval(pollTimer);}}}catch{}},1000);}

document.querySelectorAll(".output-option input").forEach(input=>input.addEventListener("change",()=>input.closest("label").classList.toggle("active",input.checked)));
$("analyzeButton").addEventListener("click",analyze);
$("downloadButton").addEventListener("click",download);
$("pasteButton").addEventListener("click",async()=>{try{$("urlInput").value=await navigator.clipboard.readText();}catch{toast(lang==="zh"?"请长按输入框粘贴":"Long-press the field to paste");}});
$("cancelButton").addEventListener("click",async()=>{if(currentJob)await api("/api/cancel",{method:"POST",body:JSON.stringify({id:currentJob.id})});});
$("settingsButton").addEventListener("click",()=>show("settingsModal"));
$("pairButton").addEventListener("click",()=>show("pairModal"));
document.querySelectorAll("[data-close]").forEach(el=>el.addEventListener("click",()=>hide(el.dataset.close)));
document.querySelectorAll(".modal").forEach(el=>el.addEventListener("click",event=>{if(event.target===el)hide(el.id);}));
$("languageSelect").addEventListener("change",event=>{lang=event.target.value;localStorage.setItem("videograb-lang",lang);applyLanguage();if(currentJob)renderJob(currentJob);});
$("fontSelect").value=localStorage.getItem("videograb-scale")||"1";
document.documentElement.style.setProperty("--scale",$("fontSelect").value);
$("fontSelect").addEventListener("change",event=>{localStorage.setItem("videograb-scale",event.target.value);document.documentElement.style.setProperty("--scale",event.target.value);});
$("browserSelect").value=localStorage.getItem("videograb-browser")||"";
$("browserSelect").addEventListener("change",event=>localStorage.setItem("videograb-browser",event.target.value));
window.addEventListener("beforeinstallprompt",event=>{event.preventDefault();installPrompt=event;});
$("installButton").addEventListener("click",async()=>{if(installPrompt){installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;}else toast(t("installHint"));});
if("serviceWorker" in navigator)navigator.serviceWorker.register("/sw.js").catch(()=>{});
applyLanguage();connect();
