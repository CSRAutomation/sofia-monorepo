class State:
    """
    Encapsulamiento de todos los estados utilizado durante la conversacion, seran mandados a traer
    cuando el usuario use palabras clave, agrupamiento por category para tener una mejor claridad y organizacion
    """

    class Customer:
        FULL_NAME = "full_name"
        FIRST_NAME = "first_name"
        LAST_NAME = "last_name"
        NAME_GATHERED = "customer_name_gathered"
        DOB = "dob"
        PHONE = "phone"
        EMAIL = "email"
        SSN = "ssn"
        CALLE = "calle"
        CIUDAD = "ciudad"
        CODIGO_POSTAL = "codigo_postal"
        PAIS = "pais"
        AÑO_AYUDA_TAXES = "año_ayuda_taxes"

    class Representative:
        IS_REPRESENTATIVE = "is_representative"
        FULL_NAME = "representative_full_name"
        FIRST_NAME = "representative_first_name"
        LAST_NAME = "representative_last_name"
        NAME_GATHERED = "representative_name_gathered"
        RELATIONSHIP = "representative_relationship"
        RELATIONSHIP_GATHERED = "representative_relationship_gathered"

    class Account:
        ID = "account_id"

    class Case:
        CLIENT_FOUND = "case_client_found"
        CLIENT_SEARCH_ATTEMPTED = "case_client_search_attempted"
        CLIENT_VERIFIED = "case_client_verified"
        CLIENT_VERIFICATION_ATTEMPTED = "case_client_verification_attempted"
        CLIENT_VERIFICATION_ATTEMPTS = "case_client_verification_attempts"
        CUSTOMER_SERVICE_CREATED = "case_customer_service_created"
    
    class Customer_Service:
        CALL_TYPE = "customer_service_call_type" # Esto se llena si la llamada la hicimos nosotros o la realizo el cliente a nosotros
        RELATIONSHIP = "customer_service_relationship" # la relacion que tiene el cliente con el usuario cuando la llamada es por un representante
        REASON_CONTACT = "customer_service_reason_contact" #Aqui debemos guardar la solicitud del cliente o la intencion, en salesforce este campo aparece como fast_note y es campo requerido para crear un new customer servie.
        LAST_HELP_YEAR = "customer_service_last_help_year" #Aqui se define el ultimo anio de ayuda en el cual se le apoyo al usuario con esto nos ayudamos a definir el tipo de cliente
        CHANNEL = "customer_service_channel" # Debe ser seleccionado el canal por el cual se fue contactado
        CLIENT_TYPE = "customer_service_client_type" #Depende del ultimo ano el el que se le dio apoyo o si es cliente nueo se define directamente como cliente nuevo
        MOOD = "customer_service_mood" # Aqui se debe capturar el estado de animo del cliente detectado durante la conversacion

    class Script_Customer_Servie:
        pass