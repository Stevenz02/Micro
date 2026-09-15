const ref = (name) => ({ $ref: `#/components/schemas/${name}` });
const response = (description, schema) => ({ description, content: { 'application/json': { schema } } });
const error = (description) => response(description, ref('Error'));
export const openapi = {
  openapi: '3.0.3',
  info: { title: 'Reto 2 - Departamentos', version: '2.0.0', description: 'API independiente con persistencia PostgreSQL.' },
  servers: [{ url: '/' }],
  components: { schemas: {
    Departamento: {
      type: 'object', required: ['id', 'nombre', 'descripcion'], additionalProperties: false,
      properties: {
        id: { type: 'string', minLength: 1, description: 'Identificador único', example: 'IT' },
        nombre: { type: 'string', minLength: 1, description: 'Nombre del departamento', example: 'Tecnología' },
        descripcion: { type: 'string', minLength: 1, description: 'Descripción del departamento', example: 'Departamento de TI' },
      },
    },
    Error: { type: 'object', required: ['detail'], properties: { detail: { type: 'string' } } },
    Salud: { type: 'object', required: ['status'], properties: { status: { type: 'string', enum: ['ok'] } } },
  } },
  paths: {
    '/departamentos': {
      post: { tags: ['Departamentos'], summary: 'Crear departamento',
        requestBody: { required: true, content: { 'application/json': { schema: ref('Departamento') } } },
        responses: { 201: response('Departamento creado', ref('Departamento')), 400: error('Datos inválidos o id duplicado'),
          413: error('Cuerpo demasiado grande'), 500: error('Error interno'), 503: error('Base de datos no disponible') },
      },
      get: { tags: ['Departamentos'], summary: 'Listar departamentos', responses: {
        200: response('Departamentos registrados', { type: 'array', items: ref('Departamento') }),
        500: error('Error interno'), 503: error('Base de datos no disponible'),
      } },
    },
    '/departamentos/{id}': { get: { tags: ['Departamentos'], summary: 'Consultar departamento',
      parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'string' }, description: 'Identificador del departamento' }],
      responses: { 200: response('Departamento encontrado', ref('Departamento')), 404: error('Departamento inexistente'),
        500: error('Error interno'), 503: error('Base de datos no disponible') },
    } },
    '/health': { get: { tags: ['Salud'], summary: 'Comprobar API y esquema de BD', responses: {
      200: response('Servicio listo', ref('Salud')), 500: error('Esquema no disponible'), 503: error('Base de datos no disponible'),
    } } },
  },
};
