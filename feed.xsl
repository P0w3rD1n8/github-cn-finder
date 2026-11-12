<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" encoding="UTF-8" indent="no"/>
  <xsl:template match="/">
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title><xsl:value-of select="rss/channel/title"/></title>
        <style>
          body{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.7;margin:0;padding:0 0 40px}
          .wrap{max-width:720px;margin:0 auto;padding:24px 16px}
          h1{font-size:24px;margin:0 0 6px}
          .sub{color:#8b949e;font-size:13px;margin-bottom:20px}
          .item{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 16px;margin-bottom:12px}
          .item a{color:#58a6ff;text-decoration:none;font-size:16px;font-weight:600}
          .item .meta{color:#8b949e;font-size:12px;margin-top:4px}
          .item p{color:#c9d1d9;font-size:13.5px;margin:8px 0 0}
          .hint{color:#8b949e;font-size:13px;margin-top:24px;border-top:1px dashed #30363d;padding-top:14px}
          .hint a{color:#a371f7}
        </style>
      </head>
      <body>
        <div class="wrap">
          <h1><xsl:value-of select="rss/channel/title"/></h1>
          <div class="sub"><xsl:value-of select="rss/channel/description"/></div>
          <xsl:for-each select="rss/channel/item">
            <div class="item">
              <a href="{link}"><xsl:value-of select="title"/></a>
              <div class="meta"><xsl:value-of select="pubDate"/></div>
              <p><xsl:value-of select="description"/></p>
            </div>
          </xsl:for-each>
          <div class="hint">
            这是一个 RSS 订阅源。想订阅每周更新？
            <a href="{rss/channel/link}../subscribe/">点这里看怎么用 →</a>
          </div>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
