import http from 'k6/http';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const VUS = __ENV.VUS || 50;
const DURATION = __ENV.DURATION || '60s';

export const options = {
  vus: VUS,
  duration: DURATION,
};

export default function () {
  group('Petstore Example', function () {
    // List all pets
    let listPetsRes = http.get(`${BASE_URL}/pets`, {
      headers: {},
    });
    check(listPetsRes, {
      'status is 200': (r) => r.status === 200,
    });
    sleep(1);

    // Get pet by id
    let getPetByIdRes = http.get(`${BASE_URL}/pets/string`, {
      headers: {},
    });
    check(getPetByIdRes, {
      'status is 200': (r) => r.status === 200,
    });
    sleep(1);
  });
}