import http from 'k6/http';
import { check, group, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL ? __ENV.BASE_URL : 'http://127.0.0.1:8000';
const VUS = __ENV.VUS ? parseInt(__ENV.VUS) : 10;
const DURATION = __ENV.DURATION ? __ENV.DURATION : '60s';

export const options = {
    vus: VUS,
    duration: DURATION,
};

export default function () {
    let authToken = __ENV.TOKEN ? __ENV.TOKEN : null;
    group('Auth', function () {
        group('Login', function () {
            const url = `${BASE_URL}/api/auth/login`;
            const payload = JSON.stringify({
                username: 'momo',
                password: 'ab123456'
            });
            const params = {
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            const res = http.post(url, payload, params);

            check(res, {
                'login status is 2xx or 200': (r) => r.status >= 200 && r.status < 300,
            });

            if (res.status >= 200 && res.status < 300) {
                const body = res.json();
                if (body && body.data && body.data.accessToken) {
                    authToken = body.data.accessToken;
                } else if (body && body.accessToken) {
                    authToken = body.accessToken;
                }
            }
            sleep(1);
        });

        if (authToken) {
            group('Logout', function () {
                const url = `${BASE_URL}/api/auth/logout`;
                const params = {
                    headers: {
                        'Authorization': `Bearer ${authToken}`,
                    },
                };

                const res = http.post(url, null, params);

                check(res, {
                    'logout status is 2xx or 200': (r) => r.status >= 200 && r.status < 300,
                });
                sleep(1);
            });
        }
    });
}