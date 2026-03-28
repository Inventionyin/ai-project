import http from 'k6/http';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const VUS = __ENV.VUS || 50;
const DURATION = __ENV.DURATION || '60s';
const TOKEN = __ENV.TOKEN || null;

export const options = {
    vus: VUS,
    duration: DURATION,
};

let authToken = TOKEN;

export default function () {
    if (authToken === null) {
        group('5. 认证(Auth)', function () {
            const loginPayload = JSON.stringify({
                username: 'momo',
                password: 'ab123456'
            });
            const loginHeaders = {
                'Content-Type': 'application/json',
            };
            const loginRes = http.post(`${BASE_URL}/api/auth/login`, loginPayload, { headers: loginHeaders });
            const checkLogin = loginRes.status >= 200 && loginRes.status < 300;
            if (!checkLogin) {
                console.error(`Login failed: ${loginRes.status} ${loginRes.body}`);
            }
            const loginJson = loginRes.json();
            if (loginJson && loginJson.data && loginJson.data.accessToken) {
                authToken = loginJson.data.accessToken;
            } else if (loginJson && loginJson.accessToken) {
                authToken = loginJson.accessToken;
            } else if (loginJson && loginJson.data && loginJson.data.token) {
                authToken = loginJson.data.token;
            } else if (loginJson && loginJson.token) {
                authToken = loginJson.token;
            }
            sleep(1);
        });
    }
}