import type { Metadata } from "next"
import Script from "next/script"
import { Geist, Geist_Mono, Manrope, Plus_Jakarta_Sans } from "next/font/google"
import { Toaster } from "sonner"
import { ThemeProvider } from "@/components/layout/theme-provider"
import "./globals.css"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

// Manrope — body / UI. Plus Jakarta Sans — display / headings.
const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  display: "swap",
})

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
  display: "swap",
})

export const metadata: Metadata = {
  title: "DreamTalk — Create your digital twin",
  description:
    "DreamTalk transforms your voice and appearance into an interactive digital human — multilingual, expressive, and local-first.",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} ${manrope.variable} ${jakarta.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        {/* ── Hydration & Console Defense ──────────────────────────────── */}
        {/* This inline script runs synchronously during HTML parsing before */}
        {/* any JS modules or extension content scripts load. It:            */}
        {/* 1. Blocks fdprocessedid attribute injection by browser extensions */}
        {/* 2. Suppresses THREE.Clock deprecation warnings (Three.js r183+) */}
        {/* 3. Removes any fdprocessedid attrs already in the DOM          */}
        {/* 4. Watches for future injection via MutationObserver           */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){
              var __ow=console.warn;
              console.warn=function(){
                var msg=arguments[0];
                if(msg&&typeof msg==='string'&&(msg.indexOf('THREE.Clock')>=0||msg.indexOf('THREE.')>=0&&msg.indexOf('deprecated')>=0))return;
                return __ow.apply(console,arguments)
              };
              var __origSetAttr=Element.prototype.setAttribute;
              Element.prototype.setAttribute=function(n,v){
                if(n==='fdprocessedid')return;
                return __origSetAttr.call(this,n,v)
              };
              try{
                var __all=document.querySelectorAll('[fdprocessedid]');
                for(var __i=0;__i<__all.length;__i++)__all[__i].removeAttribute('fdprocessedid');
              }catch(e){}
              try{
                new MutationObserver(function(muts){
                  for(var j=0;j<muts.length;j++){
                    var m=muts[j];
                    if(m.type==='attributes'&&m.attributeName==='fdprocessedid')m.target.removeAttribute('fdprocessedid');
                  }
                }).observe(document.documentElement,{attributes:true,subtree:true,attributeFilter:['fdprocessedid']});
              }catch(e){}
            })()`
          }}
        />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        {/* Secondary suppression runs right before interactive code loads */}
        <Script id="pre-hydration-console-patch" strategy="beforeInteractive">
          {`(function(){
            var __ow2=console.warn;
            console.warn=function(){
              var msg=arguments[0];
              if(msg&&typeof msg==='string'&&(msg.indexOf('THREE.Clock')>=0||msg.indexOf('THREE.')>=0&&msg.indexOf('deprecated')>=0))return;
              return __ow2.apply(console,arguments)
            };
          })()`}
        </Script>
        <ThemeProvider>
          {children}
          <Toaster position="top-center" richColors closeButton />
        </ThemeProvider>
      </body>
    </html>
  )
}
