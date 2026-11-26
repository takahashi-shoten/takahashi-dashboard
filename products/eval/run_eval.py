import json, os, random, re, sys, time, requests
G=os.environ["GEMINI_API_KEY"]; A=os.environ.get("ANTHROPIC_API_KEY","")
def gem(prompt, model="gemini-3.8-flash"):
    r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",headers={"x-goog-api-key":G},json={"contents":[{"parts":[{"text":prompt}]}]},timeout=120)
    r.raise_for_status(); j=r.json(); u=j.get("usageMetadata",{})
    return "".join(p.get("text","") for p in j["candidates"][0]["content"]["parts"] if not p.get("thought")), (u.get("promptTokenCount",0),u.get("candidatesTokenCount",0)+u.get("thoughtsTokenCount",0))
def cla(prompt, model="claude-haiku-5-5"):
    r=requests.post("https://api.anthropic.com/v1/messages",headers={"x-api-key":A,"anthropic-version":"2023-06-01"},json={"model":model,"max_tokens":1500,"messages":[{"role":"user","content":prompt}]},timeout=120)
    r.raise_for_status(); j=r.json(); return j["content"][0]["text"], (j["usage"]["input_tokens"],j["usage"]["output_tokens"])
GEN={"gemini":gem,"claude":cla}
def retry(f,*a):
    for i in range(3):
        try: return f(*a)
        except Exception as e:
            err=str(e)[:200]; time.sleep(5)
    return "[ERROR] "+err,(0,0)
reviews=json.load(open("products/p1_review_reply/testcases.json",encoding="utf-8"))
body=open("products/p1_review_reply/prompt.md",encoding="utf-8").read().split("## プロンプト本文\n",1)[1]
def p1_B(t): return body.replace("【ここに入力: 業種・店名・地域(例: 美容室○○/○○市)】","美容室(サンプル店)").replace("【ここに入力: 丁寧/親しみやすい/落ち着いた のどれか】","丁寧").replace("【ここに入力: 口コミ本文をそのまま貼る】",t)
def p1_A(t): return "美容室のGoogleマップの口コミに、店として返信を書いてください。口コミ: "+t
memos=[open("products/p3_receipt_memo/testcases.txt",encoding="utf-8").read().strip(),
"11/3 28,000 居酒屋 取引先と飲み会\n11/6 9,800 家電量販店 PC用モニター\n11/9 3,000 ガソリン スタンド(仕事と私用)\n11/15 55,000 家賃 自宅兼事務所",
"11/1 1,200 書店 業務の本\n11/12 6,600 美容院 カット\n11/18 480 コンビニ 切手\n11/25 33,000 セミナー 参加費"]
exp=[sum(int(x.replace(",","")) for x in re.findall(r"^\d+/\d+\s+([\d,]+)",m,re.M)) for m in memos]
P3B=open("products/p3_receipt_memo/prompt.md",encoding="utf-8").read().split("プロンプト本文:\n",1)[1]
def p3_B(m): return P3B.replace("【ここにメモを貼る】",m)
def p3_A(m): return "この支出メモを経費の表にまとめて。\n"+m
BAN=["絶対","必ず","No.1","ナンバーワン","全員","100%","保証","治る"]
def chk_p1(case,out):
    r=out.strip(); kw=re.findall(r"カット|カラー|雰囲気|説明|仕上がり|髪色|写真|15分|待ち|態度|対応|接客|大声|最悪",case["text"])
    d={"length":120<=len(r)<=220,"nobanned":not any(b in r for b in BAN),"thanks":any(w in r[:25] for w in ["ありがとう","お礼"]),"quote":any(k in r for k in kw)}
    if case["stars"]<=2: d["apology"]=1<=r.count("申し訳")+r.count("お詫び")<=2
    return d
def chk_p3(i,out):
    tot=exp[i]; s=out.replace(",","")
    return {"total":str(tot) in s,"disclaimer":any(w in out for w in ["専門家","税理士","税務署"]) and "確認" in out,"noassert":not any(w in out for w in ["全額経費にできます","必ず経費","節税できます","問題ありません"])}
def judge(kind,gen_family,x,y,ctx):
    jf=cla if gen_family=="gemini" else gem
    q={"p1":"小さな美容室の店主です。次の口コミに、Googleマップで店として返信します。下のXとYのうち、そのまま(または最小限の修正で)投稿したいのはどちらですか。誇大な表現・言い訳・口コミに無い事実の追加・不適切な表現があれば減点してください。","p3":"個人事業主です。確定申告の前に支出メモを整理したいです。XとYのうち、安全に役立つのはどちらですか。計算の誤り・断定的な税務判断・私用の混在の見落としは減点してください。"}[kind]
    p=f"{q}\n\n入力:\n{ctx}\n\n[X]\n{x}\n\n[Y]\n{y}\n\n最初の行に X か Y か 引き分け のどれか1語だけ、次の行に理由を1行で書いてください。"
    t,_=retry(jf,p); first=t.strip().split("\n")[0]
    return "X" if first.startswith("X") else "Y" if first.startswith("Y") else "tie"
rng=random.Random(20261126); R=[]; cost={"gemini":[0,0],"claude":[0,0]}
def gen(fam,p):
    t,u=retry(GEN[fam],p); cost[fam][0]+=u[0]; cost[fam][1]+=u[1]; return t
for fam,runs in (("gemini",3),("claude",1)):
    for run in range(runs):
        for c in reviews:
            a=gen(fam,p1_A(c["text"])); b=gen(fam,p1_B(c["text"]))
            R.append(dict(kind="p1",fam=fam,run=run,id=c["id"],A=a,B=b,chkA=chk_p1(c,a),chkB=chk_p1(c,b),ctx=f"星{c['stars']}: {c['text']}"))
        for i,m in enumerate(memos):
            a=gen(fam,p3_A(m)); b=gen(fam,p3_B(m))
            R.append(dict(kind="p3",fam=fam,run=run,id=f"m{i}",A=a,B=b,chkA=chk_p3(i,a),chkB=chk_p3(i,b),ctx=m))
for r in R:
    swap=rng.random()<0.5; x,y=(r["B"],r["A"]) if swap else (r["A"],r["B"])
    v=judge(r["kind"],r["fam"],x,y,r["ctx"]); r["judge"]="tie" if v=="tie" else ("B" if (v=="X")==swap else "A"); r["swap"]=swap
def rate(rows,k): 
    t=[v for r in rows for v in r[k].values()]; 
    return round(100*sum(t)/len(t),1) if t else None
S={}
for kind in ("p1","p3"):
    for fam in ("gemini","claude"):
        rows=[r for r in R if r["kind"]==kind and r["fam"]==fam]
        nt=[r for r in rows if r["judge"]!="tie"]
        S[f"{kind}/{fam}"]=dict(n=len(rows),check_A=rate(rows,"chkA"),check_B=rate(rows,"chkB"),judge_B=sum(r["judge"]=="B" for r in rows),judge_A=sum(r["judge"]=="A" for r in rows),judge_tie=sum(r["judge"]=="tie" for r in rows),errors=sum(r["A"].startswith("[ERROR]") or r["B"].startswith("[ERROR]") for r in rows))
print("TOKENS",json.dumps(cost)); print("SUMMARY",json.dumps(S,ensure_ascii=False,indent=1))
os.makedirs("products/eval/out",exist_ok=True); json.dump(R,open("products/eval/out/results.json","w",encoding="utf-8"),ensure_ascii=False)
