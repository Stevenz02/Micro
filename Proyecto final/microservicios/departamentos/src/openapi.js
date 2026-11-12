const ref = (name) => ({ $ref: `#/components/schemas/${name}` });
const response = (description, schema) => ({ description, content: { 'application/json': { schema } } });
const error = (description) => response(description, ref('Error'));
export const openapi = {
  openapi: '3.0.3',
  info: { title: 'Proyecto final - Departamentos', version: '1.0.0', description: 'API independiente con persistencia PostgreSQL.' },
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
    DepartamentoActualizacion: {
      type: 'object', required: ['nombre', 'descripcion'], additionalProperties: false,
      properties: {
        nombre: { type: 'string', minLength: 1, example: 'Tecnología' },
        descripcion: { type: 'string', minLength: 1, example: 'Departamento de TI y plataformas' },
      },
    },
    Error: { type: 'object', required: ['detail'], properties: { detail: { type: 'string' } } },
    Salud: { type: 'object', required: ['status', 'service', 'checks'], properties: { status: { type: 'string', enum: ['UP', 'DOWN'] }, service: { type: 'string' }, checks: { type: 'object', additionalProperties: { type: 'string', enum: ['UP', 'DOWN'] } } } },
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
    '/departamentos/{id}': {
      parameters: [{ name: 'id', in: 'path', required: true, schema: { type: 'string' }, description: 'Identificador del departamento' }],
      get: { tags: ['Departamentos'], summary: 'Consultar departamento',
        responses: { 200: response('Departamento encontrado', ref('Departamento')), 404: error('Departamento inexistente'),
          500: error('Error interno'), 503: error('Base de datos no disponible') },
      },
      put: { tags: ['Departamentos'], summary: 'Actualizar nombre y descripción (el id es inmutable)',
        requestBody: { required: true, content: { 'application/json': { schema: ref('DepartamentoActualizacion') } } },
        responses: { 200: response('Departamento actualizado', ref('Departamento')), 400: error('Datos inválidos'),
          404: error('Departamento inexistente'), 500: error('Error interno'), 503: error('Base de datos no disponible') },
      },
      delete: { tags: ['Departamentos'], summary: 'Eliminar departamento',
        responses: { 204: { description: 'Departamento eliminado' }, 404: error('Departamento inexistente'),
          500: error('Error interno'), 503: error('Base de datos no disponible') },
      },
    },
    '/health': { get: { tags: ['Salud'], summary: 'Comprobar API y esquema de BD', responses: {
      200: response('Servicio listo', ref('Salud')), 503: response('Servicio degradado (BD caída)', ref('Salud')),
    } } },
  },
};
