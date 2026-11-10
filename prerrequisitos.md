# Prerrequisitos del taller en Free Edition

Esta variante corre en Databricks Free Edition, con una cuenta gratuita por participante. Es la alternativa si su workspace de desarrollo no tiene listos los permisos del taller: no depende de su administrador, porque cada persona tiene su propio workspace y el setup crea el catálogo. La práctica es la misma, con datos sintéticos que imitan las tablas de comisiones y con un ATL reducido que construí para el taller.

## 1. Una cuenta de Free Edition por participante

Créenla antes del taller en la [página de registro de Free Edition](https://www.databricks.com/learn/free-edition). Al registrarse, Databricks crea un workspace nuevo con compute serverless y almacenamiento por defecto ([Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition)).

Tengan en cuenta sus límites ([límites de Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)):

- Es para uso personal y no comercial, con una cuota de uso. Si se supera, el compute del workspace se apaga por el resto del día, sin borrar datos ni configuración. El taller consume poco, pero eviten correr otras cargas ese día.
- Solo hay compute serverless, y la salida a internet está restringida a un grupo de dominios de confianza.

**No suban datos ni código reales de Postobón a Free Edition.** Es una cuenta personal, fuera del gobierno de su workspace, y el taller no los necesita.

## 2. El repositorio en un Git folder

En su workspace, **Workspace > Create > Git folder**, con la URL `https://github.com/scaravacap/postobon-genie-code-sdd-workshop-free-edition`. Es público, así que no hace falta configurar credenciales de Git ([Git folders](https://docs.databricks.com/aws/en/repos/repos-setup)).

Si la red de la oficina bloquea github.com, avísenme y les llevo el paquete para importarlo con **Import**.

## 3. Genie Code en su workspace

Abran un notebook, conéctenlo a serverless y abran el panel de Genie Code. Pídanle algo simple, por ejemplo "¿qué versión de Python tiene este notebook?". Si responde, está listo.

## 4. Laptop con navegador

Cada persona con su laptop y su sesión abierta en su workspace de Free Edition. Si la red de la oficina restringe sitios, comprueben antes que el workspace abre desde ahí.

Para el Lab 5, que es opcional y para después del taller, también necesitan la [CLI de Databricks](https://docs.databricks.com/aws/en/dev-tools/cli/install) con un perfil hacia su workspace ([autenticación](https://docs.databricks.com/aws/en/dev-tools/cli/authentication)).

## Lista para comprobar antes del taller

- [ ] Tienen su cuenta de Free Edition y el workspace abre desde la red de la oficina.
- [ ] El Git folder del repositorio clona.
- [ ] Genie Code responde en un notebook con serverless.
