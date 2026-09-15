"""Prueba opcional de Swagger UI con Edge headless y Playwright.

Requiere el Compose habitual vacío en 8080/8081. Crea IT y E001 por Swagger.
Instalar herramienta: python -m pip install playwright
Ejecutar desde la raíz: python -m Reto_2.tests.swagger_browser
"""
import json

from playwright.sync_api import sync_playwright

from Reto_1.app.models import EMPLEADO_EJEMPLO


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        try:
            for port, resource, body in [
                (8081, 'departamentos', {'id': 'IT', 'nombre': 'Tecnología', 'descripcion': 'Departamento de TI'}),
                (8080, 'empleados', EMPLEADO_EJEMPLO),
            ]:
                page = browser.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://localhost:{port}/docs', wait_until='networkidle')
                page.locator('.opblock').first.wait_for(timeout=30000)
                assert page.locator('.opblock').count() == 4
                for method, expected in [('post', 201), ('get', 200)]:
                    operation = page.locator(f'.opblock-{method}').filter(
                        has=page.locator(f'.opblock-summary-path[data-path="/{resource}"]')
                    )
                    operation.locator('.opblock-summary').click()
                    operation.get_by_role('button', name='Try it out').click()
                    if method == 'post':
                        operation.locator('textarea').fill(json.dumps(body, ensure_ascii=False))
                    with page.expect_response(lambda response: response.url.endswith(f'/{resource}')
                                              and response.request.method == method.upper()) as pending:
                        operation.get_by_role('button', name='Execute', exact=True).click()
                    response = pending.value
                    assert response.status == expected, (resource, method, response.status, response.text())
                    if method == 'post':
                        assert response.json() == body
                    else:
                        assert body in response.json()
                assert not errors, errors
                print(f'OK Swagger {resource}: render, POST 201, GET 200 y sin errores JavaScript', flush=True)
                page.close()
        finally:
            browser.close()


if __name__ == '__main__':
    main()
