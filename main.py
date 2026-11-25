from datetime import datetime
from pathlib import Path
import sqlite3
from colorama import Back, Fore, Style, init

# CONFIGURACIÓN DE RUTAS
BASE_DIR = Path(__file__).resolve().parent
RUTA_DB = BASE_DIR / "inventario.db"
CARPETA_LOGS = BASE_DIR / "logs"
RUTA_LOG = CARPETA_LOGS / "inventario.log"


def registrar_log(nivel: str, mensaje: str) -> None:
    """Agrega una línea con fecha y hora al archivo de log."""
    CARPETA_LOGS.mkdir(parents=True, exist_ok=True)
    fecha_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    linea = f"{fecha_hora} | {nivel} | {mensaje}\n"
    try:
        with open(RUTA_LOG, "a", encoding="utf-8") as archivo:
            archivo.write(linea)
    except OSError as error:
        print(Fore.RED + f"❌ No se pudo escribir el log: {error}")


# MENSAJES CON COLORAMA
def mostrar_exito(texto: str) -> None:
    print(Fore.GREEN + f"✅ {texto}")


def mostrar_error(texto: str) -> None:
    print(Fore.RED + f"❌ {texto}")


def mostrar_aviso(texto: str) -> None:
    print(Fore.YELLOW + f"⚠️ {texto}")


def mostrar_titulo(texto: str) -> None:
    print()
    print(Fore.CYAN + Style.BRIGHT + f"=== {texto} ===")


# BASE DE DATOS
def ejecutar_consulta(sql: str, parametros: tuple = (), traer_datos: bool = False):
    """Ejecuta una consulta parametrizada en SQLite, hace rollback ante error y cierra la conexión."""
    conexion = sqlite3.connect(RUTA_DB)
    try:
        cursor = conexion.cursor()
        cursor.execute(sql, parametros)

        if traer_datos:
            return cursor.fetchall()

        conexion.commit()
        return cursor.rowcount
    except sqlite3.Error as error:
        conexion.rollback()
        mostrar_error(f"Error en la base de datos: {error}")
        registrar_log("ERROR", f"Base de datos: {error}")
        return [] if traer_datos else 0
    finally:
        conexion.close()


def inicializar_base_de_datos() -> None:
    """Crea la tabla productos si no existe."""
    sql = """
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            cantidad INTEGER NOT NULL,
            precio REAL NOT NULL,
            categoria TEXT
        )
    """
    ejecutar_consulta(sql)
    registrar_log("INFO", "Programa iniciado. Tabla 'productos' verificada.")


# VALIDACIONES 
def pedir_texto(mensaje: str, obligatorio: bool = True, actual: str | None = None) -> str:
    """Pide texto limpio; si hay valor actual y se presiona Enter, lo conserva."""
    while True:
        if actual is not None:
            texto = input(f"{mensaje} [{actual}]: ").strip()
            return actual if texto == "" else texto

        texto = input(f"{mensaje}: ").strip()
        if texto == "" and obligatorio:
            mostrar_error("Este campo no puede estar vacío.")
            continue
        return texto


def pedir_entero(mensaje: str, actual: int | None = None) -> int:
    """Pide un entero no negativo; si hay valor actual y se presiona Enter, lo conserva."""
    while True:
        if actual is not None:
            texto = input(f"{mensaje} [{actual}]: ").strip()
            if texto == "":
                return actual
        else:
            texto = input(f"{mensaje}: ").strip()

        if not texto.isdigit():
            mostrar_error("Ingresá un número entero válido (ej: 10).")
            continue

        numero = int(texto)
        if numero < 0:
            mostrar_error("El número no puede ser negativo.")
            continue
        return numero


def pedir_decimal(mensaje: str, actual: float | None = None) -> float:
    """Pide un número decimal no negativo (acepta coma o punto)."""
    while True:
        if actual is not None:
            texto = input(f"{mensaje} [{actual}]: ").strip()
            if texto == "":
                return actual
        else:
            texto = input(f"{mensaje}: ").strip()

        try:
            numero = float(texto.replace(",", "."))
            if numero < 0:
                mostrar_error("El número no puede ser negativo.")
                continue
            return numero
        except ValueError:
            mostrar_error("Ingresá un número válido (ej: 1500.50).")


def confirmar(mensaje: str) -> bool:
    respuesta = input(f"{mensaje} (s/n): ").strip().lower()
    return respuesta == "s"


# VISUALIZACIÓN Y CONSULTAS 
def imprimir_producto_detallado(prod: tuple) -> None:
    prod_id, nombre, descripcion, cantidad, precio, categoria = prod
    if cantidad == 0:
        stock_msg = Fore.RED + f"Cantidad: {cantidad} (¡SIN STOCK!)"
    else:
        stock_msg = Fore.GREEN + f"Cantidad: {cantidad}"

    desc_texto = descripcion if descripcion else "-"
    cat_texto = categoria if categoria else "-"
    print(
        f"✅ ID: {prod_id} | Nombre: {nombre} | Descripción: {desc_texto} | "
        f"{stock_msg} | Precio: ${precio:.2f} | Categoría: {cat_texto}"
    )


def obtener_producto_por_id(id_producto: int):
    filas = ejecutar_consulta(
        "SELECT id, nombre, descripcion, cantidad, precio, categoria FROM productos WHERE id = ?",
        (id_producto,),
        traer_datos=True,
    )
    return filas[0] if filas else None


# FUNCIONALIDADES Y REPORTES
def agregar_producto() -> None:
    mostrar_titulo("REGISTRAR NUEVO PRODUCTO")
    nombre = pedir_texto("Nombre del producto")
    descripcion = pedir_texto("Descripción (opcional)", obligatorio=False)
    cantidad = pedir_entero("Cantidad disponible")
    precio = pedir_decimal("Precio del producto")
    categoria = pedir_texto("Categoría (opcional)", obligatorio=False)

    sql = """
        INSERT INTO productos (nombre, descripcion, cantidad, precio, categoria)
        VALUES (?, ?, ?, ?, ?)
    """
    filas_afectadas = ejecutar_consulta(sql, (nombre, descripcion, cantidad, precio, categoria))
    if filas_afectadas > 0:
        mostrar_exito(f"¡Producto '{nombre}' registrado con éxito!")
        registrar_log(
            "INFO",
            f"Producto registrado: '{nombre}' (cantidad: {cantidad}, precio: {precio:.2f})",
        )


def mostrar_productos() -> None:
    mostrar_titulo("LISTA DE PRODUCTOS REGISTRADOS")
    productos = ejecutar_consulta(
        "SELECT id, nombre, descripcion, cantidad, precio, categoria FROM productos ORDER BY id",
        traer_datos=True,
    )
    if not productos:
        mostrar_error("Todavía no hay productos cargados en el inventario.")
    else:
        for prod in productos:
            imprimir_producto_detallado(prod)
        print(Fore.CYAN + "-" * 70)
        print(f"Total: {len(productos)} producto(s)")

    registrar_log("INFO", "Se consultó el listado de productos.")


def buscar_producto() -> None:
    mostrar_titulo("BUSCAR PRODUCTO (POR ID O NOMBRE)")
    busqueda = pedir_texto("Ingresá el ID o parte del nombre a buscar")

    if busqueda.isdigit():
        resultados = ejecutar_consulta(
            "SELECT id, nombre, descripcion, cantidad, precio, categoria FROM productos WHERE id = ?",
            (int(busqueda),),
            traer_datos=True,
        )
    else:
        resultados = ejecutar_consulta(
            "SELECT id, nombre, descripcion, cantidad, precio, categoria FROM productos WHERE nombre LIKE ? ORDER BY id",
            (f"%{busqueda}%",),
            traer_datos=True,
        )

    if not resultados:
        mostrar_error(f"No se encontró ningún producto con '{busqueda}'.")
    else:
        mostrar_exito(f"Se encontraron {len(resultados)} producto(s):")
        for prod in resultados:
            imprimir_producto_detallado(prod)

    registrar_log("INFO", f"Búsqueda realizada: '{busqueda}' ({len(resultados)} resultado(s)).")


def actualizar_producto() -> None:
    mostrar_titulo("ACTUALIZAR PRODUCTO POR ID")
    id_producto = pedir_entero("Ingresá el ID del producto a actualizar")
    prod_actual = obtener_producto_por_id(id_producto)

    if prod_actual is None:
        mostrar_error(f"No existe ningún producto con el ID {id_producto}.")
        return

    _, nombre, descripcion, cantidad, precio, categoria = prod_actual
    mostrar_exito(f"Producto encontrado: {nombre}")
    mostrar_aviso("Presioná Enter para mantener el valor actual.")

    nuevo_nombre = pedir_texto("Nuevo nombre", actual=nombre)
    nueva_desc = pedir_texto("Nueva descripción", actual=descripcion or "")
    nueva_cantidad = pedir_entero("Nueva cantidad", actual=cantidad)
    nuevo_precio = pedir_decimal("Nuevo precio", actual=precio)
    nueva_cat = pedir_texto("Nueva categoría", actual=categoria or "")

    sql = """
        UPDATE productos
        SET nombre = ?, descripcion = ?, cantidad = ?, precio = ?, categoria = ?
        WHERE id = ?
    """
    filas_afectadas = ejecutar_consulta(
        sql,
        (nuevo_nombre, nueva_desc, nueva_cantidad, nuevo_precio, nueva_cat, id_producto),
    )
    if filas_afectadas > 0:
        mostrar_exito(f"¡Producto ID {id_producto} actualizado con éxito!")
        registrar_log("INFO", f"Producto actualizado: ID {id_producto} ('{nuevo_nombre}')")


def eliminar_producto() -> None:
    mostrar_titulo("ELIMINAR PRODUCTO POR ID")

    productos = ejecutar_consulta(
        "SELECT id, nombre, descripcion, cantidad, precio, categoria FROM productos ORDER BY id",
        traer_datos=True,
    )
    if not productos:
        mostrar_error("No hay productos cargados para eliminar.")
        return

    for prod in productos:
        imprimir_producto_detallado(prod)
    print(Fore.CYAN + "-" * 70)

    id_producto = pedir_entero("Ingresá el ID del producto a eliminar")
    prod = obtener_producto_por_id(id_producto)

    if prod is None:
        mostrar_error(f"No se encontró ningún producto con el ID {id_producto}.")
        return

    mostrar_aviso("Vas a eliminar este producto:")
    imprimir_producto_detallado(prod)
    if not confirmar(f"¿Estás seguro de eliminar '{prod[1]}' (ID: {id_producto})?"):
        mostrar_aviso("Operación cancelada.")
        return

    filas_afectadas = ejecutar_consulta("DELETE FROM productos WHERE id = ?", (id_producto,))
    if filas_afectadas > 0:
        mostrar_exito(f"Producto '{prod[1]}' eliminado correctamente.")
        registrar_log("WARNING", f"Producto eliminado: ID {id_producto} ('{prod[1]}')")


def reporte_stock_bajo() -> None:
    mostrar_titulo("REPORTE DE STOCK BAJO")
    limite = pedir_entero("Mostrar productos con cantidad menor o igual a")

    resultados = ejecutar_consulta(
        "SELECT id, nombre, descripcion, cantidad, precio, categoria FROM productos WHERE cantidad <= ? ORDER BY cantidad ASC, id ASC",
        (limite,),
        traer_datos=True,
    )

    if not resultados:
        mostrar_exito(f"¡Genial! No hay productos con stock menor o igual a {limite}.")
    else:
        mostrar_aviso(
            f"ATENCIÓN: Se encontraron {len(resultados)} producto(s) con stock bajo o agotado:"
        )
        for prod in resultados:
            imprimir_producto_detallado(prod)

    registrar_log("INFO", f"Reporte de stock bajo consultado (límite <= {limite}).")


# MENÚ 
def encabezado() -> None:
    print()
    print(Back.GREEN + Fore.WHITE + Style.BRIGHT + "=" * 51)
    print(Back.GREEN + Fore.WHITE + Style.BRIGHT + "   SISTEMA DE GESTION DE PRODUCTOS - INVENTARIO   ")
    print(Back.GREEN + Fore.WHITE + Style.BRIGHT + "=" * 51)


def mostrar_menu() -> None:
    print()
    print(Back.GREEN + Fore.WHITE + Style.BRIGHT + "                   MENU PRINCIPAL                  ")
    print(Back.GREEN + Fore.WHITE + " 1. Registrar nuevo producto                       ")
    print(Back.GREEN + Fore.WHITE + " 2. Mostrar productos registrados                  ")
    print(Back.GREEN + Fore.WHITE + " 3. Buscar producto (por ID o nombre)              ")
    print(Back.GREEN + Fore.WHITE + " 4. Actualizar producto por ID                     ")
    print(Back.GREEN + Fore.WHITE + " 5. Eliminar producto por ID                       ")
    print(Back.GREEN + Fore.WHITE + " 6. Reporte de stock bajo                          ")
    print(Back.GREEN + Fore.WHITE + " 7. Salir                                          ")
    print(Back.GREEN + Fore.WHITE + Style.BRIGHT + "=" * 51)


def main() -> None:
    inicializar_base_de_datos()
    encabezado()

    acciones = {
        "1": agregar_producto,
        "2": mostrar_productos,
        "3": buscar_producto,
        "4": actualizar_producto,
        "5": eliminar_producto,
        "6": reporte_stock_bajo,
    }

    while True:
        mostrar_menu()
        opcion = input("Elegí una opción (1-7): ").strip()

        if opcion == "7":
            registrar_log("INFO", "Programa finalizado.")
            mostrar_exito("👋 Gracias por usar nuestro sistema de inventario.")
            break
        elif opcion in acciones:
            acciones[opcion]()
        else:
            mostrar_error("Opción inválida, intentá de nuevo.")


if __name__ == "__main__":
    main()