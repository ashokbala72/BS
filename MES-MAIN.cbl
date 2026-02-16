       IDENTIFICATION DIVISION.
       PROGRAM-ID. MES-MAIN.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT INVENTORY-FILE ASSIGN TO "inventory.dat"
               ORGANIZATION IS INDEXED
               ACCESS MODE IS DYNAMIC
               RECORD KEY IS INV-PART-NO.

           SELECT PRODUCTION-FILE ASSIGN TO "production.dat"
               ORGANIZATION IS SEQUENTIAL.

           SELECT SUPPLIER-FILE ASSIGN TO "supplier.dat"
               ORGANIZATION IS INDEXED
               ACCESS MODE IS DYNAMIC
               RECORD KEY IS SUPPLIER-ID.

       DATA DIVISION.
       FILE SECTION.

       FD INVENTORY-FILE.
       01 INVENTORY-RECORD.
           05 INV-PART-NO            PIC X(15).
           05 INV-DESCRIPTION        PIC X(50).
           05 INV-ON-HAND            PIC 9(7).
           05 INV-REORDER-LEVEL      PIC 9(7).
           05 INV-UNIT-COST          PIC 9(5)V99.
           05 INV-HOLDING-COST       PIC 9(5)V99.
           05 INV-ANNUAL-DEMAND      PIC 9(7).
           05 INV-ORDERING-COST      PIC 9(5)V99.
           05 INV-CRITICALITY        PIC X(10).

       FD PRODUCTION-FILE.
       01 PRODUCTION-RECORD.
           05 PROD-ORDER-NO          PIC X(12).
           05 PROD-PART-NO           PIC X(15).
           05 PROD-QUANTITY          PIC 9(7).
           05 PROD-WORK-CENTER       PIC X(10).
           05 PROD-STATUS            PIC X(10).
           05 PROD-START-DATE        PIC 9(8).
           05 PROD-END-DATE          PIC 9(8).

       FD SUPPLIER-FILE.
       01 SUPPLIER-RECORD.
           05 SUPPLIER-ID            PIC X(10).
           05 SUPPLIER-NAME          PIC X(50).
           05 SUPPLIER-RATING        PIC 9(3).
           05 SUPPLIER-PRICE         PIC 9(5)V99.
           05 SUPPLIER-LEAD-TIME     PIC 9(3).
           05 SUPPLIER-PAYMENT-TERMS PIC X(20).

       WORKING-STORAGE SECTION.

       01 WS-EOF                     PIC X VALUE "N".
       01 WS-EOQ                     PIC 9(7)V99.
       01 WS-TOTAL-COST              PIC 9(9)V99.
       01 WS-DELIVERY-TIME           PIC X(20).
       01 WS-ACTION                  PIC X(20).
       01 WS-STATUS                  PIC X(20).
       01 WS-MARKET-TREND            PIC X(20).

       PROCEDURE DIVISION.

       MAIN-SECTION.
           PERFORM INIT-PROCESS
           PERFORM PROCESS-PRODUCTION
           PERFORM INVENTORY-CHECK
           PERFORM SUPPLIER-EVALUATION
           PERFORM FINALIZE-PROCESS
           STOP RUN.

       INIT-PROCESS.
           DISPLAY "MES SYSTEM STARTED".

       PROCESS-PRODUCTION.
           OPEN INPUT PRODUCTION-FILE
           PERFORM UNTIL WS-EOF = "Y"
               READ PRODUCTION-FILE
                   AT END MOVE "Y" TO WS-EOF
                   NOT AT END
                       PERFORM VALIDATE-ORDER
                       PERFORM UPDATE-INVENTORY
               END-READ
           END-PERFORM
           CLOSE PRODUCTION-FILE.

       VALIDATE-ORDER.
           IF PROD-QUANTITY <= 0
               DISPLAY "INVALID ORDER QUANTITY"
           END-IF
           IF PROD-STATUS = "PLANNED"
               MOVE "IN-PROGRESS" TO PROD-STATUS
           END-IF.

       UPDATE-INVENTORY.
           OPEN I-O INVENTORY-FILE
           MOVE PROD-PART-NO TO INV-PART-NO
           READ INVENTORY-FILE
               INVALID KEY DISPLAY "PART NOT FOUND"
               NOT INVALID KEY
                   SUBTRACT PROD-QUANTITY FROM INV-ON-HAND
                   REWRITE INVENTORY-RECORD
           END-READ
           CLOSE INVENTORY-FILE.

       INVENTORY-CHECK.
           OPEN INPUT INVENTORY-FILE
           PERFORM UNTIL WS-EOF = "Y"
               READ INVENTORY-FILE
                   AT END MOVE "Y" TO WS-EOF
                   NOT AT END
                       PERFORM CALCULATE-EOQ
                       PERFORM CHECK-REORDER
               END-READ
           END-PERFORM
           CLOSE INVENTORY-FILE.

       CALCULATE-EOQ.
           COMPUTE WS-EOQ =
             FUNCTION SQRT(
                (2 * INV-ANNUAL-DEMAND * INV-ORDERING-COST)
                / INV-HOLDING-COST
             ).

       CHECK-REORDER.
           IF INV-ON-HAND < INV-REORDER-LEVEL
               MOVE "REORDER" TO WS-ACTION
               PERFORM DETERMINE-DELIVERY
           END-IF.

       DETERMINE-DELIVERY.
           IF INV-CRITICALITY = "high"
               MOVE "<15 days" TO WS-DELIVERY-TIME
           ELSE
               IF INV-CRITICALITY = "medium"
                   MOVE "15-30 days" TO WS-DELIVERY-TIME
               ELSE
                   MOVE "30-60 days" TO WS-DELIVERY-TIME
               END-IF
           END-IF.

       SUPPLIER-EVALUATION.
           OPEN INPUT SUPPLIER-FILE
           READ SUPPLIER-FILE
               AT END DISPLAY "NO SUPPLIER"
               NOT AT END
                   PERFORM CALCULATE-TOTAL-COST
                   PERFORM DETERMINE-PREFERRED-SUPPLIER
           END-READ
           CLOSE SUPPLIER-FILE.

       CALCULATE-TOTAL-COST.
           COMPUTE WS-TOTAL-COST =
             WS-EOQ * SUPPLIER-PRICE.

       DETERMINE-PREFERRED-SUPPLIER.
           IF SUPPLIER-RATING > 80
               MOVE "PREFERRED" TO WS-STATUS
           ELSE
               MOVE "REVIEW" TO WS-STATUS
           END-IF.

       FINALIZE-PROCESS.
           DISPLAY "MES SYSTEM COMPLETED".
