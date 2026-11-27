"""Données de test réalistes (flux RSS et pages article) servies par un faux serveur HTTP."""
FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>
<title>Journal de test</title><link>https://journal.test/</link>
<item><title>Le budget de l'État augmente</title><link>https://www.journal.test/economie/budget-etat/?utm_source=rss</link>
<description>&lt;p&gt;Les recettes fiscales progressent.&lt;/p&gt;</description>
<pubDate>Mon, 23 Nov 2026 08:30:00 +0300</pubDate><media:content url="https://journal.test/img/budget.jpg" medium="image"/></item>
<item><title>Match de football à Mahamasina</title><link>https://journal.test/sport/match-mahamasina</link>
<description>Victoire des Barea.</description></item>
<item><title>Article daté du futur</title><link>https://journal.test/divers/futur</link>
<description>Date aberrante.</description><pubDate>Mon, 01 Jan 2035 00:00:00 +0000</pubDate></item>
</channel></rss>"""


def article_page(title: str, body_word: str, date: str | None = "2026-11-23T08:30:00+03:00") -> str:
    para = (f"<p>{body_word} fait l'objet d'une longue analyse par les services concernés, qui détaillent les "
            "mesures adoptées cette semaine à Antananarivo et leurs conséquences pour les ménages et les entreprises. "
            "Les responsables ont rappelé le calendrier prévu et les engagements pris auprès des partenaires.</p>")
    meta = f'<meta property="article:published_time" content="{date}">' if date else ""
    return f"""<html><head><title>{title} - Journal</title>
<meta property="og:title" content="{title}"><meta property="og:image" content="https://journal.test/img/og.jpg">
{meta}<link rel="canonical" href="https://journal.test/page/{body_word.lower()}">
</head><body><nav>Menu Accueil Contact</nav><article><h1>{title}</h1>{para * 6}</article>
<footer>Mentions légales</footer></body></html>"""
