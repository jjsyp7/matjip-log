# 찐맛 지도 로컬 서버: 이 파일이 있는 폴더를 http://localhost:8765 로 연다.
import http.server, functools, os
here = os.path.dirname(os.path.abspath(__file__))
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=here)
http.server.ThreadingHTTPServer(("127.0.0.1", 8765), handler).serve_forever()
