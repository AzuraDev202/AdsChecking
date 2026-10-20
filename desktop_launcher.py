"""Entry point for the Windows portable distribution."""
import sys
from pathlib import Path

from adschecking.desktop import Desktop


def main():
    app = Desktop()
    if len(sys.argv) == 3 and sys.argv[1] == '--smoke-test':
        app.withdraw()
        app.update()
        assert str(app.login_button['state']) == 'disabled'
        assert str(app.proxy_button['state']) == 'normal'
        app.close()
        Path(sys.argv[2]).write_text('AdsChecking desktop smoke test passed\n', encoding='utf-8')
        return
    app.mainloop()


if __name__ == '__main__':
    main()
