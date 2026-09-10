// Dreamtalk - Frontend Animata
// Based on animata (MIT License)
// Source: animata

import { Globe, Link, MessageCircle, AtSign } from "lucide-react";

export default function Profile() {
  return (
    <div className="group/profile flex h-52 w-52 flex-col items-center justify-center rounded-3xl bg-cyan-200 p-4 shadow-sm transition-shadow duration-300 hover:shadow-black/25 dark:bg-zinc-800">
      <img
        alt=""
        src="https://images.unsplash.com/photo-1633332755192-727a05c4013d?q=80&w=800&auto=format&fit=crop"
        className="h-16 w-16 rounded-full duration-300 ease-in-out hover:scale-125"
      />
      <div className="mt-2 flex flex-col items-center justify-center">
        <h3 className="font-sans font-semibold text-foreground">Avatar Aang</h3>
        <p className="text-sm font-light text-muted-foreground">The last air bender</p>
      </div>
      <div className="mt-2 flex w-full flex-row justify-evenly rounded-3xl bg-background/70 p-2 text-foreground dark:bg-background/25">
        <a href="https://x.com/?lang=en&mx=2" target="_blank" rel="noopener noreferrer">
          <AtSign size={18} className="transition-transform duration-300 hover:scale-110" />
        </a>
        <a href="https://linkedin.com/" target="_blank" rel="noopener noreferrer">
          <Link size={16} className="transition-transform duration-300 hover:scale-110" />
        </a>
        <a href="https://dribbble.com/" target="_blank" rel="noopener noreferrer">
          <Globe size={16} className="transition-transform duration-300 hover:scale-110" />
        </a>
        <a href="https://facebook.com/" target="_blank" rel="noopener noreferrer">
          <MessageCircle size={16} className="duration-300 hover:scale-110" />
        </a>
      </div>
    </div>
  );
}
