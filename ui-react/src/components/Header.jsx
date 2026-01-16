export default function Header({ activeNav = 'explore' }) {
    return (
        <header className="header">
            <div className="header-content">
                <a href="/" className="logo">
                    <svg className="logo-icon" viewBox="0 0 265.61 193.96" width="32" height="24">
                        <path d="M0,0V193.96H88.81V109.6h87.98v84.36h88.81V0h-88.81V82.17H88.81V0H0Z" fill="currentColor" />
                    </svg>
                    <span>HackFind</span>
                </a>
                <nav className="nav">
                    <a href="#" className={`nav-link ${activeNav === 'explore' ? 'active' : ''}`}>Explore</a>
                    <a href="#" className={`nav-link ${activeNav === 'saved' ? 'active' : ''}`}>Saved</a>
                    <a href="#" className={`nav-link ${activeNav === 'about' ? 'active' : ''}`}>About</a>
                </nav>
            </div>
        </header>
    );
}
