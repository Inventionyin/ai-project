import http from 'k6/http';
import { check, group, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const VUS = __ENV.VUS ? parseInt(__ENV.VUS) : 50;
const DURATION = __ENV.DURATION || '60s';

export const options = {
  vus: VUS,
  duration: DURATION,
};

let authToken = __ENV.TOKEN || null;

export default function () {
  group('Authentication', function () {
    const loginPayload = JSON.stringify({
      username: 'momo',
      password: 'ab123456',
    });

    const loginHeaders = {
      'Content-Type': 'application/json',
    };

    const loginRes = http.post(`${BASE_URL}/api/auth/login`, loginPayload, { headers: loginHeaders });

    check(loginRes, {
      'login status is 200': (r) => r.status === 200,
      'login response code is 0': (r) => r.json('code') === 0,
    });

    if (loginRes.status === 200 && loginRes.json('code') === 0) {
      const token = loginRes.json('data.accessToken') || loginRes.json('accessToken') || loginRes.json('data.token') || loginRes.json('token');
      if (token) {
        authToken = token;
      }
    }

    sleep(1);
  });
}