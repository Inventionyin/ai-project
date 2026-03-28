import http from 'k6/http';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:5173';
const VUS = __ENV.VUS || 50;
const DURATION = __ENV.DURATION || '60s';

export const options = {
  vus: VUS,
  duration: DURATION,
};

let token = __ENV.TOKEN || null;

export default function () {
  group('5. 认证(Auth)', function () {
    const loginApi = {
      name: '5.4 Register',
      feature: '5. 认证(Auth)',
      method: 'POST',
      url: '/api/auth/register',
      params: {
        phone: 'demo',
        username: 'demo',
        password: 'demo',
        confirmPassword: 'demo',
        captcha: 'demo',
      },
      headers: {},
      expectedStatusCode: null,
    };

    let requestUrl = `${BASE_URL}${loginApi.url}`;
    let requestHeaders = { ...loginApi.headers };
    let requestBody = null;

    if (['POST', 'PUT', 'PATCH'].includes(loginApi.method)) {
      requestHeaders['Content-Type'] = 'application/json';
      requestBody = JSON.stringify(loginApi.params);
    }

    const res = http.request(loginApi.method, requestUrl, requestBody, { headers: requestHeaders });

    const checkStatus = loginApi.expectedStatusCode ? loginApi.expectedStatusCode : [200, 201, 202, 204];
    const checkResult = check(res, {
      [`${loginApi.name} status`]: (r) => (Array.isArray(checkStatus) ? checkStatus.includes(r.status) : r.status === checkStatus),
    });

    if (checkResult && res.status >= 200 && res.status < 300) {
      try {
        const jsonRes = res.json();
        token = jsonRes.data?.accessToken || jsonRes.accessToken || jsonRes.data?.token || jsonRes.token || token;
      } catch (e) {
      }
    }

    sleep(1);
  });
}