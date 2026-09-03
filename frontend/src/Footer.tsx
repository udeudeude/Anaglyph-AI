import "./styles/Footer.css"

function Footer() {
    return (
        <footer className="footer">
            <div className="container">
                <p><strong>Anaglyph &amp; Friends</strong> · built from the original Anaglyph AI by Duy Huynh</p>
                <div className="social-links">
                    <a href="https://github.com/udeudeude/Anaglyph-AI" target="_blank" rel="noreferrer">Current fork</a>
                    <span>|</span>
                    <a href="https://github.com/Senacen/Anaglyph-AI" target="_blank" rel="noreferrer">Original project</a>
                    <span>|</span>
                    <a href="https://www.linkedin.com/in/mduyhuynh" target="_blank" rel="noreferrer">Duy Huynh</a>
                </div>
            </div>
        </footer>
    )
}

export default Footer
