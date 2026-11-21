# -*- coding: utf-8 -*-
"""고정 페이지 본문 (번체 중국어). 운영자 정보는 config.py에서 가져와요."""
import os
import sys
from html import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from update_data import INDICATORS  # noqa: E402


def zone_table():
    rows, lo = [], 0
    meaning = {
        "極度恐懼": "市場充滿悲觀，賣壓沉重。歷史上常出現在急跌之後。",
        "恐懼": "投資人偏向保守，資金觀望。",
        "中性": "多空情緒大致平衡。",
        "貪婪": "投資人偏向積極，追價意願提高。",
        "極度貪婪": "市場過熱，需留意追高與修正風險。",
    }
    for mx, name, color in C.ZONES:
        rows.append('<tr><td><span class="zone-dot" style="background:%s"></span>%s</td><td>%d–%d</td><td>%s</td></tr>'
                    % (color, name, lo, mx, meaning[name]))
        lo = mx + 1
    return '<div class="tbl"><table><thead><tr><th>區間</th><th>分數</th><th>代表的市場氣氛</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(rows)


def methodology():
    rows = "".join(
        "<tr><td><b>%s</b></td><td>%d%%</td><td>%s</td></tr>" % (n, round(w * 100), escape(d))
        for _k, n, w, _inv, _u, d in INDICATORS)
    return """
<article class="article">
<p class="crumb"><a href="/">首頁</a> › 計算方法</p>
<h1>台股恐懼貪婪指數的計算方法</h1>
<p>本站參考 CNN「Fear &amp; Greed Index」的設計概念，改用<b>台灣市場的公開資料</b>，將市場情緒整理成 0 到 100 的分數。分數越低代表越恐懼，越高代表越貪婪。以下完整公開計算方式，讓每一位讀者都能檢視數字的由來。</p>

<h2>一、七項指標與權重</h2>
<div class="tbl"><table><thead><tr><th>指標</th><th>權重</th><th>看什麼</th></tr></thead><tbody>%s</tbody></table></div>

<h2>二、分數怎麼算</h2>
<ol>
<li><b>每項指標換算成 0–100 分</b>：把當天的數值放進「過去一年（約 252 個交易日）」的分布裡，看它排在第幾百分位。例如融資餘額變化率高於過去一年 80%% 的日子，就得到 80 分。</li>
<li><b>方向一致</b>：波動率、Put/Call 比、美元兌新台幣這三項是「越高越恐懼」，因此以 100 減去百分位。</li>
<li><b>加權平均</b>：七項分數依上表權重平均。若某項資料當天無法取得，該項暫不計入，其餘指標依比例重新分配權重，並在首頁標示。</li>
<li><b>三日平滑</b>：為避免單日雜訊，首頁顯示的是最近三個交易日的平均分數。</li>
</ol>

<h2>三、分數區間</h2>
%s

<h2>四、資料來源與更新時間</h2>
<div class="tbl"><table><thead><tr><th>資料</th><th>來源</th></tr></thead><tbody>
<tr><td>加權指數收盤價</td><td>Yahoo Finance（^TWII），備援：臺灣證券交易所</td></tr>
<tr><td>上漲／下跌家數、融資餘額、外資買賣超</td><td>臺灣證券交易所 盤後資訊</td></tr>
<tr><td>台指選擇權 Put/Call 比</td><td>臺灣期貨交易所</td></tr>
<tr><td>美元兌新台幣</td><td>Yahoo Finance（TWD=X）</td></tr>
<tr><td>美股恐懼貪婪指數</td><td>CNN Business（原始數值，本站未加工）</td></tr>
</tbody></table></div>
<p>台股收盤後（約 15:40）與晚間（約 21:40）各更新一次；美股指數於台灣時間清晨更新。遇國定假日或颱風休市則不更新。</p>

<h2>五、使用限制</h2>
<ul>
<li>本指數描述的是「目前的市場情緒」，並非預測未來漲跌的模型。</li>
<li>台股恐懼貪婪指數與 CNN 美股指數、日本與韓國指數的計算方式不同，<b>不宜直接比較數字高低</b>，比較「方向」與「變化」較有意義。</li>
<li>官方資料偶有修正，本站會依最新資料重新計算，因此過去的分數可能出現 1–2 分的差異。</li>
</ul>
<p class="disclaimer">本站內容僅供資訊參考，不構成任何投資建議。投資前請審慎評估自身風險承受度。</p>
</article>""" % (rows, zone_table())


def guide():
    return """
<article class="article">
<p class="crumb"><a href="/">首頁</a> › 新手指南</p>
<h1>新手指南：恐懼貪婪指數是什麼？該怎麼看？</h1>
<p>「別人貪婪時我恐懼，別人恐懼時我貪婪。」這句投資名言提醒我們，市場常常被情緒推著走。恐懼貪婪指數就是把這種情緒變成一個看得見的數字，幫助你在追高或殺低之前，先停下來想一想。</p>
<h2>一、一個數字看懂市場溫度</h2>
<p>指數介於 0 到 100。可以把它想成「市場溫度計」：溫度太低（極度恐懼）時，大家急著賣；溫度太高（極度貪婪）時，大家搶著買。</p>
%s
<h2>二、為什麼要另外做「台股版」？</h2>
<p>CNN 的指數只看美股。台股有自己的特色，例如<b>外資持股比重高</b>、<b>散戶常用融資</b>、<b>台指選擇權交易活絡</b>，以及<b>新台幣匯率</b>會反映資金進出。本站把這些在地資料納入計算，更貼近台灣投資人的實際感受。</p>
<h2>三、四個市場一起看</h2>
<p>首頁同時列出台灣、美國、日本、韓國的指數。台股與美股、日韓股市連動緊密，當四個市場同時陷入恐懼，通常代表全球性的風險事件；若只有台股特別恐懼，則可能是在地因素（例如權值股財報、外資大量賣超）。</p>
<h2>四、正確的使用方式</h2>
<ul>
<li>把它當成<b>情緒背景參考</b>，搭配基本面與自己的投資計畫。</li>
<li>留意<b>變化速度</b>：三天內從 70 掉到 30，比長期停在 30 更值得注意。</li>
<li>極端值不等於轉折點：極度恐懼可能持續一段時間，請做好資金控管。</li>
</ul>
<p>想了解每項指標的細節，請參考<a href="/methodology">計算方法</a>；每天的變化與解讀，請看<a href="/blog/">市場日報</a>。</p>
<p class="disclaimer">本站內容僅供資訊參考，不構成任何投資建議。</p>
</article>""" % zone_table()


def about():
    return """
<article class="article">
<p class="crumb"><a href="/">首頁</a> › 關於我們</p>
<h1>關於我們</h1>
<p>{name}（{en}）是一個專注於「市場情緒」的資訊網站。我們以臺灣證券交易所、臺灣期貨交易所等公開資料，每天計算台股恐懼貪婪指數，並同時整理美國、日本、韓國的情緒指標，讓讀者用一個畫面掌握亞洲與美國市場的氣氛。</p>
<h2>我們的原則</h2>
<ul>
<li><b>計算方式公開透明</b>：所有指標、權重與資料來源都寫在<a href="/methodology">計算方法</a>頁面。</li>
<li><b>不推薦個股、不提供買賣建議</b>：本站只描述市場情緒，不是投資顧問。</li>
<li><b>錯誤即時更正</b>：若發現資料或文章有誤，會在原文標註更正日期與內容。</li>
</ul>
<h2>營運資訊</h2>
<div class="tbl"><table><tbody>
<tr><th>網站名稱</th><td>{name}（{en}）</td></tr>
<tr><th>營運者</th><td>{op}</td></tr>
<tr><th>聯絡信箱</th><td><a href="mailto:{mail}">{mail}</a></td></tr>
<tr><th>成立日期</th><td>{launch}</td></tr>
<tr><th>姊妹站</th><td>日本 Fear &amp; Greed、韓國 Fear &amp; Greed</td></tr>
</tbody></table></div>
</article>""".format(name=escape(C.SITE_NAME), en=escape(C.SITE_NAME_EN), op=escape(C.OPERATOR_NAME),
                     mail=escape(C.CONTACT_EMAIL), launch=C.LAUNCH_DATE.replace("-", "/"))


def privacy():
    return """
<article class="article">
<p class="crumb"><a href="/">首頁</a> › 隱私權政策</p>
<h1>隱私權政策</h1>
<p>{name}（以下稱「本站」）重視您的隱私，並依中華民國《個人資料保護法》處理個人資料。請詳閱以下說明。</p>
<h2>一、蒐集的資料</h2>
<p>本站不需註冊即可使用。您主動來信時，我們會取得您的電子郵件地址與來信內容，僅用於回覆您的詢問。</p>
<h2>二、Cookie 與第三方服務</h2>
<p>本站使用 Google Analytics 分析流量，並可能使用 Google AdSense 刊登廣告。Google 等第三方供應商會使用 Cookie，依據使用者先前造訪本站或其他網站的紀錄放送廣告。Google 使用廣告 Cookie，讓 Google 及其合作夥伴能依據使用者造訪本站和（或）網路上其他網站的情形，向使用者放送合適的廣告。</p>
<p>您可以前往 <a href="https://adssettings.google.com/" rel="noopener" target="_blank">Google 廣告設定</a> 停用個人化廣告，或前往 <a href="https://www.aboutads.info/" rel="noopener" target="_blank">www.aboutads.info</a> 停用第三方供應商的 Cookie。您也可以在瀏覽器設定中拒絕 Cookie，但部分功能可能因此受限。</p>
<p>關於 Google 如何使用資料，請參考 <a href="https://policies.google.com/technologies/partner-sites?hl=zh-TW" rel="noopener" target="_blank">Google 的說明</a>。</p>
<h2>三、資料的利用與保護</h2>
<p>除法律另有規定外，本站不會將您的個人資料提供給第三方。</p>
<h2>四、您的權利</h2>
<p>您可以隨時來信要求查詢、更正或刪除您提供的個人資料：<a href="mailto:{mail}">{mail}</a></p>
<h2>五、政策修訂</h2>
<p>本政策如有修訂，將公告於本頁。</p>
<p class="small muted">制定日期：{launch}</p>
</article>""".format(name=escape(C.SITE_NAME), mail=escape(C.CONTACT_EMAIL), launch=C.LAUNCH_DATE.replace("-", "/"))


def terms():
    return """
<article class="article">
<p class="crumb"><a href="/">首頁</a> › 使用條款與免責聲明</p>
<h1>使用條款與免責聲明</h1>
<h2>一、資訊性質</h2>
<p>本站提供的指數、圖表與文章僅供一般資訊參考，<b>不構成任何投資建議、推薦或買賣有價證券之邀約</b>。本站並非證券投資顧問事業，不提供個別投資建議。</p>
<h2>二、正確性</h2>
<p>本站資料取自公開來源並自行計算，我們盡力確保正確，但不保證資料完整、即時或無誤。資料來源方修正數據時，本站分數也可能隨之調整。</p>
<h2>三、責任限制</h2>
<p>使用者依本站內容所做的任何投資決定，應自行判斷並承擔風險。因使用本站資訊所生之任何損失，本站不負賠償責任。</p>
<h2>四、著作權</h2>
<p>本站文章與圖表之著作權屬本站所有。歡迎附上出處連結引用；未經同意請勿全文轉載或用於商業用途。CNN 美股恐懼貪婪指數之權利屬 CNN 所有。</p>
<h2>五、外部連結</h2>
<p>本站可能連結至第三方網站，該等網站之內容與隱私做法不在本站責任範圍內。</p>
<h2>六、準據法</h2>
<p>本條款以中華民國法律為準據法。</p>
<p class="small muted">制定日期：{launch}</p>
</article>""".format(launch=C.LAUNCH_DATE.replace("-", "/"))


def contact():
    return """
<article class="article">
<p class="crumb"><a href="/">首頁</a> › 聯絡我們</p>
<h1>聯絡我們</h1>
<p>對本站資料、計算方法或文章有任何疑問與建議，或發現錯誤，歡迎來信：</p>
<p class="callout"><b>電子郵件：</b><a href="mailto:{mail}">{mail}</a></p>
<p>我們通常會在 3 個工作天內回覆。基於法規，本站<b>無法回答個股買賣或個人投資配置</b>的問題，敬請見諒。</p>
</article>""".format(mail=escape(C.CONTACT_EMAIL))


def not_found():
    return """
<article class="article" style="text-align:center">
<h1>找不到這個頁面</h1>
<p>頁面可能已移動或刪除。</p>
<p><a href="/">回到首頁看今天的指數 →</a></p>
</article>"""
